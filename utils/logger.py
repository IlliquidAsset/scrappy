def log_errors(data, file_path):
    errors = [item for item in data if "Error" in item]
    with open(file_path, "w") as file:
        for item in errors:
            file.write(f"{item['Error']}\n")
    print(f"Errors logged to {file_path}")
