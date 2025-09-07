from setuptools import setup, find_packages
setup(
    name="rma_receivables",
    version="14.0.0",
    description="Journal-based Receivables Hub (read-only) with WhatsApp, PDFs, and Follow-ups",
    author="You",
    author_email="you@example.com",
    packages=find_packages(),
    include_package_data=True,
    zip_safe=False,
    install_requires=["requests>=2.28.0","python-dateutil>=2.8.2"],
)
