from setuptools import find_packages, setup


with open("README.md") as f:
    long_description = f.read()


setup(
    name="sales_crm",
    version="0.0.1",
    description="Enterprise Sales CRM layer for Frappe/ERPNext",
    long_description=long_description,
    long_description_content_type="text/markdown",
    author="BLC",
    author_email="admin@example.com",
    packages=find_packages(),
    include_package_data=True,
    zip_safe=False,
    install_requires=[],
)
