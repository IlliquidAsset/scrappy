from colorama import Fore, Style, init

# Initialize colorama
init(autoreset=True)

def log_errors(data, file_path):
    """
    Logs errors found in the data to a file and prints a summary to the console.
    """
    errors = [item for item in data if "Error" in item]
    if errors:
        print(Fore.RED + Style.BRIGHT + "\n=== Errors Found ===")
        for item in errors:
            print(Fore.RED + f"Error: {item['Error']}")
        print(Fore.RED + f"\nTotal Errors: {len(errors)}")
    else:
        print(Fore.GREEN + Style.BRIGHT + "No errors found!")

    with open(file_path, "w") as file:
        for item in errors:
            file.write(f"{item['Error']}\n")

    print(Fore.YELLOW + f"\nErrors logged to: {file_path}")

def log_scraping(locale, tax_year, message):
    """
    Logs scraping events with improved formatting for CLI readability.
    """
    print(Fore.CYAN + Style.BRIGHT + "\n=== Scraping Log ===")
    print(Fore.MAGENTA + f"Locale: {locale.upper()} | Tax Year: {tax_year}")
    print(Fore.WHITE + Style.BRIGHT + f"Message: {message}")
    print(Fore.CYAN + Style.BRIGHT + "====================\n")
