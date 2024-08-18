from setuptools import setup, find_packages

setup(
    name='claude-pyrojects',
    version='0.1.1',
    description='A tool for uploading and managing projects in Claude.ai',
    long_description=open('README.md').read(),
    long_description_content_type='text/markdown',
    author='Huseyin Cevik',
    url='https://github.com/hcevikdotpy/claude-pyrojects',
    packages=find_packages(),
    include_package_data=True,
    install_requires=[
        'click',
        'requests',
        'curl_cffi',
        'tzlocal',
    ],
    entry_points={
        'console_scripts': [
            'claude-pyrojects=claude_pyrojects.cli:main',
        ],
    },
    classifiers=[
        'Programming Language :: Python :: 3',
        'Operating System :: OS Independent'
    ],
    python_requires='>=3.6',
)
