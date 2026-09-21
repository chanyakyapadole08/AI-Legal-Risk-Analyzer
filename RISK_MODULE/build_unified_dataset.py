from services.dataset_loader import save_unified_dataset


if __name__ == "__main__":
    path, count = save_unified_dataset()

    print(f"Unified dataset saved at: {path}")
    print(f"Total clauses: {count}")