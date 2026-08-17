"""
Diffusion inpainter — completes CLIPPED cells for the reconstruction layer (C).

Uses the trained DDPM (RePaint-style) to fill the missing part of a clipped
cell region, then that cell is classified and tagged INPAINTED.

DEMO-FEASIBILITY (important, and honestly disclosed):
  - On CPU, diffusion is slow. So we (a) use few denoising steps (STEPS) and
    (b) cap how many clipped cells are inpainted per image (MAX_INPAINT).
  - This makes the live reconstruction an APPROXIMATE SAMPLE, not an exhaustive
    analysis. The rigorous full analysis is in the diffusion investigation doc.
  - C is exploratory anyway, so an approximate live version is acceptable —
    but the meta flags it clearly so it's never mistaken for exhaustive.
"""

from __future__ import annotations
from pathlib import Path
from typing import List

import numpy as np
import torch
from PIL import Image

UNET_DIR = Path(__file__).resolve().parent.parent / "models" / "unet"

STEPS = 30          # few steps for speed (full analysis used 150-250)
MAX_INPAINT = 15    # cap per image for demo feasibility
IMG = 128


class DiffusionInpainter:
    def __init__(self, unet_dir: Path = UNET_DIR, steps: int = STEPS, max_inpaint: int = MAX_INPAINT):
        self.unet_dir = Path(unet_dir)
        self.steps = steps
        self.max_inpaint = max_inpaint
        self._unet = None
        self._sched = None
        self._device = "cuda" if torch.cuda.is_available() else "cpu"

    def _ensure_loaded(self):
        if self._unet is None:
            if not self.unet_dir.exists():
                raise FileNotFoundError(
                    f"Diffusion unet not found at {self.unet_dir}. "
                    "Place the unet folder (config.json + .safetensors) in backend/models/unet/."
                )
            from diffusers import UNet2DModel, DDPMScheduler
            self._unet = UNet2DModel.from_pretrained(str(self.unet_dir)).to(self._device).eval()
            self._sched = DDPMScheduler(num_train_timesteps=1000)

    def _to_tensor(self, pil: Image.Image) -> torch.Tensor:
        a = np.array(pil.convert("RGB").resize((IMG, IMG))).astype(np.float32) / 255.0
        a = (a - 0.5) / 0.5  # -> [-1, 1]
        return torch.from_numpy(a).permute(2, 0, 1)

    def _to_pil(self, t: torch.Tensor) -> Image.Image:
        a = ((t.clamp(-1, 1) + 1) / 2 * 255).permute(1, 2, 0).cpu().numpy().astype(np.uint8)
        return Image.fromarray(a)

    @torch.no_grad()
    def _inpaint_one(self, clipped_pil: Image.Image, seed: int = 0) -> Image.Image:
        """
        Place the clipped region centered on a canvas, mask the empty area, and
        let the diffusion model fill it (RePaint: keep known pixels each step).
        """
        self._ensure_loaded()
        # build canvas: clipped region at ~60% size, centered; keep-mask over it
        region = clipped_pil.convert("RGB")
        scale = int(IMG * 0.6)
        region_r = region.resize((scale, scale))
        # median background so the canvas matches smear tone
        med = np.median(np.array(region).reshape(-1, 3), axis=0).astype(np.uint8)
        canvas = np.full((IMG, IMG, 3), med, np.uint8)
        off = (IMG - scale) // 2
        canvas[off:off + scale, off:off + scale] = np.array(region_r)
        keep = np.zeros((IMG, IMG), np.float32)
        keep[off:off + scale, off:off + scale] = 1.0
        # feather the mask edge
        import cv2
        keep = cv2.GaussianBlur((keep * 255).astype(np.uint8), (17, 17), 0).astype(np.float32) / 255.0

        real = self._to_tensor(Image.fromarray(canvas)).unsqueeze(0).to(self._device)
        m = torch.from_numpy(keep).unsqueeze(0).unsqueeze(0).to(self._device)
        g = torch.Generator(device="cpu").manual_seed(seed)
        x = torch.randn(real.shape, generator=g).to(self._device)

        self._sched.set_timesteps(self.steps)
        for t in self._sched.timesteps:
            noise = torch.randn(real.shape, generator=g).to(self._device)
            known = self._sched.add_noise(real, noise, t)
            x = known * m + x * (1 - m)
            pred = self._unet(x, t, return_dict=False)[0]
            x = self._sched.step(pred, t, x, return_dict=False)[0]
        x = real * m + x * (1 - m)
        return self._to_pil(x.squeeze(0))

    def inpaint_clipped(self, clipped_crops: List[Image.Image]) -> tuple[List[Image.Image], dict]:
        """
        Inpaint up to max_inpaint clipped crops. Returns (inpainted_images, info).
        The rest (beyond the cap) are not inpainted and reported in info.
        """
        self._ensure_loaded()
        n_total = len(clipped_crops)
        to_do = clipped_crops[: self.max_inpaint]
        out = [self._inpaint_one(c, seed=i) for i, c in enumerate(to_do)]
        info = {
            "clipped_total": n_total,
            "inpainted": len(out),
            "skipped_over_cap": max(0, n_total - self.max_inpaint),
            "steps": self.steps,
            "approximate": True,
            "note": ("Live diffusion inpainting is an APPROXIMATE SAMPLE: reduced "
                     f"steps ({self.steps}) and capped at {self.max_inpaint} cells "
                     "for CPU feasibility. Full analysis is in the investigation."),
        }
        return out, info