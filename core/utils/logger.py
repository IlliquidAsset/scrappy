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

def format_cli_output(property_data, excel_file_path, error_log_path):
    """
    Format and display CLI output with improved readability.
    """
    print("\n" + "=" * 40 + "\nSummary Report\n" + "=" * 40)
    print(f"Excel file saved to: {Fore.GREEN}{excel_file_path}{Style.RESET_ALL}")
    print(f"Error log saved to: {Fore.YELLOW}{error_log_path}{Style.RESET_ALL}")

    if property_data:
        print(f"\n{Fore.CYAN}{Style.BRIGHT}Property Data Summary:{Style.RESET_ALL}")
        print(f"Total properties found: {Fore.GREEN}{len(property_data)}{Style.RESET_ALL}")

        for index, prop in enumerate(property_data[:5], start=1):
            print(f"{index}. {Fore.YELLOW}{prop.get('Matched Name', 'Unknown')}{Style.RESET_ALL} - "
                  f"{Fore.CYAN}{prop.get('Address', 'Unknown Address')}{Style.RESET_ALL}")

        if len(property_data) > 5:
            print(f"...and {len(property_data) - 5} more properties")
    else:
        print(f"\n{Fore.RED}No property data found.{Style.RESET_ALL}")

    errors = [item for item in property_data if "Error" in item]
    if errors:
        print(f"\n{Fore.RED}{Style.BRIGHT}Errors encountered:{Style.RESET_ALL}")
        for i, error in enumerate(errors[:3], 1):
            print(f"{i}. {Fore.RED}{error['Error']}{Style.RESET_ALL}")

        if len(errors) > 3:
            print(f"...and {len(errors) - 3} more errors. See log file for details.")

    print("=" * 40)
