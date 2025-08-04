# -*- coding: utf-8 -*-
import sys
import subprocess
import asyncio
from pathlib import Path
from fastapi import APIRouter, HTTPException
from src.phoenix_core.main import app, discover_and_load_modules
from src.phoenix_core.kernel.registry import registered_routers

router = APIRouter(
    prefix="/api/v1/system",
    tags=["System Actions"],
)

install_lock = asyncio.Lock()

@router.post("/install-features", status_code=202)
async def install_features():
    """
    Asynchronously install feature packages from requirements-features.txt
    and dynamically load the new modules upon completion.
    """
    if install_lock.locked():
        raise HTTPException(status_code=409, detail="Installation is already in progress.")

    async with install_lock:
        try:
            print("Starting feature package installation...")
            venv_path = Path(".venv").resolve()
            venv_python = (venv_path / "bin" / "python").resolve()

            process_env = os.environ.copy()
            process_env["VIRTUAL_ENV"] = str(venv_path)
            process_env["PATH"] = f"{venv_path / 'bin'}:{process_env.get('PATH', '')}"

            requirements_path = "requirements/requirements-features.txt"
            uv_install_command = [str(venv_python), "-m", "uv", "pip", "install", "-q", "-r", requirements_path]

            process = await asyncio.create_subprocess_exec(
                *uv_install_command,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                env=process_env
            )
            stdout, stderr = await process.communicate()

            if process.returncode != 0:
                error_message = stderr.decode().strip()
                print(f"Feature package installation failed: {error_message}")
                raise HTTPException(status_code=500, detail=f"Package installation failed: {error_message}")

            print("✅ Feature packages installed successfully.")

            print("Dynamically loading new modules...")
            discover_and_load_modules(reload=True)
            print("✅ New modules loaded.")

            return {"message": "Feature installation and module loading successful."}

        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

registered_routers.append(router)
