def log_errors(data, log_path):
    with open(log_path, "w") as log_file:
        for item in data:
            if 'error' in item:
                log_file.write(f"Error: {item}\n")
    print(f"Errors logged to {log_path}")
