import os
import shutil
import argparse

def archive_project(items_to_archive):
    """
    Archives specified files or directories by renaming and moving them.
    """
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
    archive_base_dir = os.path.join(project_root, 'archive')
    snapshot_dir = os.path.join(archive_base_dir, 'project_snapshot_v1')

    # --- Step 1: Create the snapshot directory ---
    if not os.path.exists(snapshot_dir):
        os.makedirs(snapshot_dir)
        print(f"Created snapshot directory: {snapshot_dir}")

    # --- Step 2: Iterate through the provided items ---
    for item_name in items_to_archive:
        source_path = os.path.join(project_root, item_name)

        if not os.path.exists(source_path):
            print(f"Warning: Item '{item_name}' does not exist in the project root. Skipping.")
            continue

        archived_name = f"{item_name}_archive"
        destination_path = os.path.join(snapshot_dir, archived_name)

        try:
            print(f"Archiving '{source_path}' to '{destination_path}'...")
            shutil.move(source_path, destination_path)
            print(f"Successfully archived and renamed: {item_name} -> {archived_name}")
        except Exception as e:
            print(f"Error archiving {item_name}: {e}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Archive specified parts of the project.")
    parser.add_argument('items', nargs='+', help="A list of files or directories to archive.")

    args = parser.parse_args()

    if args.items:
        archive_project(args.items)
        print("\nArchiving complete for the specified items.")
        print(f"Archived files are located in: {os.path.join('archive', 'project_snapshot_v1')}")
    else:
        print("No items specified for archiving.")
