import shutil
import os
from pathlib import Path

def move_files():
    # Use relative path since we are running from root
    base_dir = Path(".")
    src_dir = base_dir / "src"
    
    # Create src directory if it doesn't exist
    src_dir.mkdir(exist_ok=True)
    
    # Move config
    config_src = base_dir / "config"
    config_dest = src_dir / "config"
    if config_src.exists() and not config_dest.exists():
        print(f"Moving {config_src} to {config_dest}")
        shutil.move(str(config_src), str(config_dest))
        
    # Move my_garage app
    app_src = base_dir / "django_apps" / "my_garage"
    app_dest = src_dir / "my_garage"
    if app_src.exists() and not app_dest.exists():
        print(f"Moving {app_src} to {app_dest}")
        shutil.move(str(app_src), str(app_dest))
        
    # Move fastapi_services
    fastapi_src = base_dir / "fastapi_services"
    fastapi_dest = src_dir / "fastapi_services"
    if fastapi_src.exists() and not fastapi_dest.exists():
        print(f"Moving {fastapi_src} to {fastapi_dest}")
        shutil.move(str(fastapi_src), str(fastapi_dest))
        
    # Cleanup django_apps if empty
    django_apps = base_dir / "django_apps"
    if django_apps.exists():
        # Check if empty (ignoring __pycache__)
        has_files = False
        for item in django_apps.iterdir():
            if item.name != "__pycache__" and item.name != "__init__.py":
                has_files = True
                break
        
        if not has_files:
            print(f"Removing {django_apps}")
            shutil.rmtree(str(django_apps))

if __name__ == "__main__":
    move_files()
