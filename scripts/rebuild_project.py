import os
import shutil

def rebuild_project():
    """
    Rebuilds the new project structure from the archived snapshot.
    """
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
    snapshot_dir = os.path.join(project_root, 'archive', 'project_snapshot_v1')

    if not os.path.exists(snapshot_dir):
        print("Error: Snapshot directory does not exist. Cannot rebuild.")
        return

    # --- 1. Restore core directories ---
    core_dirs_to_restore = [
        'src',
        'docs',
        'tests',
        'tools'
    ]
    for dir_name in core_dirs_to_restore:
        archived_path = os.path.join(snapshot_dir, f"{dir_name}_archive")
        restore_path = os.path.join(project_root, dir_name)
        if os.path.exists(archived_path) and not os.path.exists(restore_path):
            print(f"Restoring '{archived_path}' to '{restore_path}'...")
            shutil.move(archived_path, restore_path)
            print(f"Successfully restored: {dir_name}")
        else:
            print(f"Skipping restore for {dir_name} (already exists or archive not found).")

    # --- 2. Create a new, empty HTML directory ---
    new_html_dir = os.path.join(project_root, 'HTML')
    if not os.path.exists(new_html_dir):
        os.makedirs(new_html_dir)
        print(f"Created new empty directory: {new_html_dir}")

    # --- 3. Reorganize requirements ---
    req_dir = os.path.join(project_root, 'requirements')
    archived_req_dir = os.path.join(snapshot_dir, 'requirements_archive')

    if os.path.exists(archived_req_dir):
        # First, move the whole archived folder back
        if os.path.exists(req_dir):
            shutil.rmtree(req_dir)
        shutil.move(archived_req_dir, req_dir)
        print("Restored requirements directory.")

        # Now, reorganize the files within
        base_in_path = os.path.join(req_dir, 'base.in')
        if os.path.exists(base_in_path):
            # Define new requirement files
            core_req_path = os.path.join(req_dir, 'core.in')
            cpu_req_path = os.path.join(req_dir, 'transcription_cpu.in')

            core_deps = ['fastapi', 'uvicorn', 'aiofiles', 'python-multipart', 'pydantic', 'pydantic-settings', 'sqlalchemy', 'psutil', 'pyyaml', 'typer']
            # All other deps from base.in go to the cpu file

            with open(base_in_path, 'r') as f_in, \
                 open(core_req_path, 'w') as f_core, \
                 open(cpu_req_path, 'w') as f_cpu:

                f_core.write("# Core web server dependencies\n")
                f_cpu.write("# AI/Transcription dependencies for CPU\n")

                for line in f_in:
                    dep = line.strip()
                    if not dep or dep.startswith('#'):
                        continue

                    # Find the base package name
                    pkg_name = dep.split('==')[0].split('[')[0].lower()

                    if pkg_name in core_deps:
                        f_core.write(f"{dep}\n")
                    else:
                        f_cpu.write(f"{dep}\n")

            print("Successfully split 'base.in' into 'core.in' and 'transcription_cpu.in'")
            # We can remove the old files now if we want, but let's keep them for reference
            # os.remove(base_in_path)
            # if os.path.exists(os.path.join(req_dir, 'base.txt')):
            #     os.remove(os.path.join(req_dir, 'base.txt'))
        else:
            print("Could not find base.in to reorganize.")
    else:
        print("Archived requirements not found, skipping reorganization.")

    # --- 4. Handle docs annotation (simplified) ---
    # For now, we'll just restore the docs. Annotation can be a separate step.
    docs_dir = os.path.join(project_root, 'docs')
    if os.path.exists(docs_dir):
        # We will create a new README in the restored docs
        new_readme_path = os.path.join(docs_dir, "README_V2.md")
        with open(new_readme_path, 'w') as f:
            f.write("# Documentation for Project V2\n\n")
            f.write("This directory contains documentation for the refactored project.\n")
            f.write("Some files may have been copied from the V1 archive for reference.\n")
            f.write("These files will be annotated to indicate their origin.\n")
        print("Created a new README in the docs directory.")

    print("\nProject rebuild process complete.")

if __name__ == "__main__":
    rebuild_project()
