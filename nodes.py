import json
import os
import threading
import time

import numpy as np
from PIL import Image
from PIL.PngImagePlugin import PngInfo

import folder_paths
try:
    from comfy_api.latest import Types
except Exception:  # pragma: no cover
    Types = None

try:
    from comfy.cli_args import args
except Exception:  # pragma: no cover
    class _Args:
        disable_metadata = False

    args = _Args()


class ChamSaveImage:
    def __init__(self):
        self.output_dir = folder_paths.get_output_directory()
        self.type = "output"
        self.compress_level = 4

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "images": ("IMAGE",),
                "filename_prefix": ("STRING", {"default": "ComfyUI"}),
                "save_to_comfy_temp_dir": ("BOOLEAN", {"default": False}),
                "overwrite_existing": ("BOOLEAN", {"default": False}),
                "fixed_filename_no_increment": ("BOOLEAN", {"default": False}),
                "auto_delete_after_seconds": ("INT", {"default": 0, "min": 0, "max": 86400, "step": 1}),
            },
            "hidden": {"prompt": "PROMPT", "extra_pnginfo": "EXTRA_PNGINFO"},
        }

    RETURN_TYPES = ()
    FUNCTION = "save_images"
    OUTPUT_NODE = True
    CATEGORY = "chamdev-nodes/image"

    def _resolve_output_dir(self, save_to_comfy_temp_dir: bool) -> str:
        if save_to_comfy_temp_dir and hasattr(folder_paths, "get_temp_directory"):
            return folder_paths.get_temp_directory()
        return self.output_dir

    @staticmethod
    def _fixed_name(base_name: str, batch_number: int, batch_count: int) -> str:
        # Keep deterministic names without global incrementing.
        if batch_count > 1 and "%batch_num%" not in base_name:
            return f"{base_name}_{batch_number:05}.png"
        return f"{base_name}.png"

    @staticmethod
    def _next_available_path(path: str) -> str:
        stem, ext = os.path.splitext(path)
        index = 1
        candidate = path
        while os.path.exists(candidate):
            candidate = f"{stem}_{index:05}{ext}"
            index += 1
        return candidate

    def _metadata(self, prompt, extra_pnginfo):
        if getattr(args, "disable_metadata", False):
            return None

        metadata = PngInfo()
        if prompt is not None:
            metadata.add_text("prompt", json.dumps(prompt))
        if extra_pnginfo is not None:
            for key, value in extra_pnginfo.items():
                metadata.add_text(key, json.dumps(value))
        return metadata

    @staticmethod
    def _schedule_delete(path: str, delay_seconds: int):
        if delay_seconds <= 0:
            return

        def _delete_later():
            time.sleep(delay_seconds)
            try:
                if os.path.exists(path):
                    os.remove(path)
            except OSError:
                pass

        threading.Thread(target=_delete_later, daemon=True).start()

    def save_images(
        self,
        images,
        filename_prefix="ComfyUI",
        save_to_comfy_temp_dir=False,
        overwrite_existing=False,
        fixed_filename_no_increment=False,
        auto_delete_after_seconds=0,
        prompt=None,
        extra_pnginfo=None,
    ):
        output_dir = self._resolve_output_dir(save_to_comfy_temp_dir)
        full_output_folder, filename, counter, subfolder, _ = folder_paths.get_save_image_path(
            filename_prefix, output_dir, images[0].shape[1], images[0].shape[0]
        )

        os.makedirs(full_output_folder, exist_ok=True)
        metadata = self._metadata(prompt, extra_pnginfo)
        results = []
        batch_count = len(images)

        for batch_number, image in enumerate(images):
            i = 255.0 * image.cpu().numpy()
            img = Image.fromarray(np.clip(i, 0, 255).astype(np.uint8))
            filename_with_batch = filename.replace("%batch_num%", str(batch_number))

            if fixed_filename_no_increment:
                file_name = self._fixed_name(filename_with_batch, batch_number, batch_count)
                output_path = os.path.join(full_output_folder, file_name)
                if (not overwrite_existing) and os.path.exists(output_path):
                    output_path = self._next_available_path(output_path)
                    file_name = os.path.basename(output_path)
            else:
                file_name = f"{filename_with_batch}_{counter:05}_.png"
                output_path = os.path.join(full_output_folder, file_name)
                counter += 1

            img.save(output_path, pnginfo=metadata, compress_level=self.compress_level)
            self._schedule_delete(output_path, auto_delete_after_seconds)

            results.append(
                {
                    "filename": file_name,
                    "subfolder": subfolder,
                    "type": "temp" if save_to_comfy_temp_dir else self.type,
                }
            )

        return {"ui": {"images": results}}


class ChamSaveVideo:
    def __init__(self):
        self.output_dir = folder_paths.get_output_directory()
        self.type = "output"

    @classmethod
    def INPUT_TYPES(cls):
        format_options = cls._video_format_options()
        codec_options = cls._video_codec_options()

        return {
            "required": {
                "video": ("VIDEO",),
                "filename_prefix": ("STRING", {"default": "video/ComfyUI"}),
                "format": (format_options, {"default": "auto"}),
                "codec": (codec_options, {"default": "auto"}),
                "save_to_comfy_temp_dir": ("BOOLEAN", {"default": False}),
                "overwrite_existing": ("BOOLEAN", {"default": False}),
                "fixed_filename_no_increment": ("BOOLEAN", {"default": False}),
                "auto_delete_after_seconds": ("INT", {"default": 0, "min": 0, "max": 86400, "step": 1}),
            },
            "hidden": {"prompt": "PROMPT", "extra_pnginfo": "EXTRA_PNGINFO"},
        }

    RETURN_TYPES = ()
    FUNCTION = "save_video"
    OUTPUT_NODE = True
    CATEGORY = "chamdev-nodes/video"

    def _resolve_output_dir(self, save_to_comfy_temp_dir: bool) -> str:
        if save_to_comfy_temp_dir and hasattr(folder_paths, "get_temp_directory"):
            return folder_paths.get_temp_directory()
        return self.output_dir

    @staticmethod
    def _next_available_path(path: str) -> str:
        stem, ext = os.path.splitext(path)
        index = 1
        candidate = path
        while os.path.exists(candidate):
            candidate = f"{stem}_{index:05}{ext}"
            index += 1
        return candidate

    @staticmethod
    def _schedule_delete(path: str, delay_seconds: int):
        if delay_seconds <= 0:
            return

        def _delete_later():
            time.sleep(delay_seconds)
            try:
                if os.path.exists(path):
                    os.remove(path)
            except OSError:
                pass

        threading.Thread(target=_delete_later, daemon=True).start()

    @staticmethod
    def _video_format_options():
        fallback = ["auto", "mp4", "webm", "mov", "mkv", "avi", "gif", "webp"]
        if Types is None or not hasattr(Types, "VideoContainer"):
            return fallback
        try:
            options = []
            for item in Types.VideoContainer.as_input():
                value = getattr(item, "value", item)
                options.append(str(value))
            return options or fallback
        except Exception:
            return fallback

    @staticmethod
    def _video_codec_options():
        fallback = ["auto", "h264", "h265", "av1", "vp9", "prores"]
        if Types is None or not hasattr(Types, "VideoCodec"):
            return fallback
        try:
            options = []
            for item in Types.VideoCodec.as_input():
                value = getattr(item, "value", item)
                options.append(str(value))
            return options or fallback
        except Exception:
            return fallback

    @staticmethod
    def _resolve_extension(format_name: str) -> str:
        fallback_map = {
            "auto": "mp4",
            "mp4": "mp4",
            "webm": "webm",
            "mov": "mov",
            "mkv": "mkv",
            "avi": "avi",
            "gif": "gif",
            "webp": "webp",
        }

        if Types is not None and hasattr(Types, "VideoContainer"):
            try:
                return Types.VideoContainer.get_extension(format_name)
            except Exception:
                pass
        return fallback_map.get(str(format_name).lower(), "mp4")

    @staticmethod
    def _resolve_video_dimensions(video):
        if hasattr(video, "get_dimensions"):
            dims = video.get_dimensions()
            if isinstance(dims, (tuple, list)) and len(dims) >= 2:
                return int(dims[0]), int(dims[1])
        raise ValueError("Invalid VIDEO input: missing get_dimensions().")

    @staticmethod
    def _save_video_core_style(video, output_path: str, format_name: str, codec_name: str, metadata):
        save_kwargs = {
            "codec": codec_name,
            "metadata": metadata,
        }

        if Types is not None and hasattr(Types, "VideoContainer"):
            try:
                save_kwargs["format"] = Types.VideoContainer(format_name)
            except Exception:
                save_kwargs["format"] = format_name
        else:
            save_kwargs["format"] = format_name

        video.save_to(output_path, **save_kwargs)

    def save_video(
        self,
        video,
        filename_prefix="video/ComfyUI",
        format="auto",
        codec="auto",
        save_to_comfy_temp_dir=False,
        overwrite_existing=False,
        fixed_filename_no_increment=False,
        auto_delete_after_seconds=0,
        prompt=None,
        extra_pnginfo=None,
    ):
        output_dir = self._resolve_output_dir(save_to_comfy_temp_dir)
        width, height = self._resolve_video_dimensions(video)
        full_output_folder, filename, counter, subfolder, _ = folder_paths.get_save_image_path(
            filename_prefix, output_dir, width, height
        )
        os.makedirs(full_output_folder, exist_ok=True)

        saved_metadata = None
        if not getattr(args, "disable_metadata", False):
            metadata = {}
            if extra_pnginfo is not None:
                metadata.update(extra_pnginfo)
            if prompt is not None:
                metadata["prompt"] = prompt
            if len(metadata) > 0:
                saved_metadata = metadata

        file_ext = self._resolve_extension(format)
        base_filename = filename.replace("%batch_num%", "0")
        if fixed_filename_no_increment:
            file_name = f"{base_filename}.{file_ext}"
            output_path = os.path.join(full_output_folder, file_name)
            if (not overwrite_existing) and os.path.exists(output_path):
                output_path = self._next_available_path(output_path)
                file_name = os.path.basename(output_path)
        else:
            file_name = f"{base_filename}_{counter:05}_.{file_ext}"
            output_path = os.path.join(full_output_folder, file_name)

        self._save_video_core_style(video, output_path, format, codec, saved_metadata)

        self._schedule_delete(output_path, auto_delete_after_seconds)

        return {
            "ui": {"videos": [{"filename": file_name, "subfolder": subfolder, "type": "temp" if save_to_comfy_temp_dir else self.type}]}
        }


NODE_CLASS_MAPPINGS = {
    "ChamSaveImage": ChamSaveImage,
    "ChamSaveVideo": ChamSaveVideo,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "ChamSaveImage": "Champdev Save Image",
    "ChamSaveVideo": "Champdev Save video",
}
