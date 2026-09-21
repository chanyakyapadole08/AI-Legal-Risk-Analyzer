from datasets import load_dataset
import os


def save_dataset(dataset_name, subset, output_dir):
    os.makedirs(output_dir, exist_ok=True)

    try:
        if subset:
            ds = load_dataset(dataset_name, subset)
        else:
            ds = load_dataset(dataset_name)

        ds.save_to_disk(output_dir)

        print(f"Saved {dataset_name} {subset} to {output_dir}")

    except Exception as e:
        print(f"Failed to download {dataset_name} {subset}: {e}")


if __name__ == "__main__":
    # LEDGAR is commonly available through LexGLUE
    save_dataset(
        dataset_name="lex_glue",
        subset="ledgar",
        output_dir="datasets/LEDGAR/raw"
    )

    # ContractNLI is also commonly available through LexGLUE
    save_dataset(
        dataset_name="lex_glue",
        subset="contractnli",
        output_dir="datasets/ContractNLI/raw"
    )

    # CUAD availability can vary by HuggingFace mirror.
    # If this fails, download CUAD manually or use another HF dataset ID.
    save_dataset(
        dataset_name="theatticusproject/cuad",
        subset=None,
        output_dir="datasets/CUAD/raw"
    )
    