# Restructuring Plan: Moving to `src/` Layout with Pixi

This plan outlines the steps to migrate the current project structure to a `src/` based layout and fully integrate Pixi as the package manager.

## Current Structure
```
my_garage/
├── config/
├── django_apps/
│   └── my_garage/
├── fastapi_services/
├── manage.py
├── pixi.toml
├── pyproject.toml
└── ...
```

## Target Structure
```
my_garage/
├── src/
│   ├── config/              # Moved from root
│   ├── my_garage/           # Moved from django_apps/my_garage
│   │   ├── api/
│   │   ├── models.py
│   │   └── ...
│   └── fastapi_services/    # Moved from root
├── manage.py                # Updated to point to src
├── pixi.toml                # Updated dependencies and tasks
├── pyproject.toml           # Updated build system
└── ...
```

## Migration Steps

### Phase 1: Preparation
1.  **Backup**: Ensure all changes are committed (Git check).
2.  **Create `src` Directory**: Create the new root for source code.

### Phase 2: Move Files
1.  **Move Config**: Move `config/` to `src/config/`.
2.  **Move Django App**: Move `django_apps/my_garage/` to `src/my_garage/`.
3.  **Move FastAPI**: Move `fastapi_services/` to `src/fastapi_services/`.
4.  **Cleanup**: Remove empty `django_apps/` directory.

### Phase 3: Update References
1.  **Update `manage.py`**: Add `src` to `sys.path` or update imports.
2.  **Update `config/settings/base.py`**:
    *   Update `BASE_DIR` calculation.
    *   Update `INSTALLED_APPS` to refer to `my_garage` directly (or `src.my_garage` if installed as package).
    *   Update `ROOT_URLCONF`.
    *   Update `WSGI_APPLICATION`.
3.  **Update `config/wsgi.py` & `config/asgi.py`**: Update settings module path if needed.
4.  **Update `config/celery_app.py`**: Update settings module path.
5.  **Update Imports**:
    *   Search for `django_apps.my_garage` and replace with `my_garage`.
    *   Search for `config.` and ensure it resolves correctly (if `src` is in python path).

### Phase 4: Pixi & Build Configuration
1.  **Update `pyproject.toml`**:
    *   Update `[tool.setuptools.packages.find]` to look in `src`.
    *   Ensure `package_dir = {"": "src"}` is set.
2.  **Update `pixi.toml`**:
    *   Ensure dependencies are correct.
    *   Update tasks if paths changed (e.g. `fastapi` task).
    *   Add `pip install -e .` behavior or ensure `src` is in PYTHONPATH.

### Phase 5: Verification
1.  **Install**: Run `pixi install`.
2.  **Test Django**: Run `pixi run server`.
3.  **Test Celery**: Run `pixi run worker`.
4.  **Test FastAPI**: Run `pixi run fastapi`.
5.  **Run Tests**: Run `pixi run test`.

## Execution

I will now proceed with these steps.
