from setuptools import setup, find_packages

setup(
    name="scrappy",
    version="1.0.0",
    description="Property Data Scraping Tool",
    author="IlliquidAsset",
    packages=find_packages(),
    include_package_data=True,
    python_requires=">=3.9",
    install_requires=[
        'fastapi',
        'uvicorn',
        'flask',
        'flask-cors',
        'flask-sqlalchemy',
        'sqlalchemy',
        'requests',
        'beautifulsoup4',
        'rapidfuzz',
        'python-dotenv',
        'termcolor',
        'colorama',
        'pydantic',
        'psycopg2-binary',
        'openpyxl',
        'gunicorn',
        'python-multipart',
    ]
)
