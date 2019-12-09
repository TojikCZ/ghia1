import setuptools

with open('README.rst') as f:
    long_description = ''.join(f.readlines())

setuptools.setup(
    name='ghia_joziftom',
    version='0.5.1',
    description='Assigns people to issues based on config files',
    long_description=long_description,
    long_description_content_type="text/plain",
    author='Tomáš Jozífek',
    author_email='tojik@tojik.cz',
    keywords='github,issue,automation,webapp',
    license='GNU GPLv3',
    url='https://github.com/TojikCZ/ghia1',
    packages=setuptools.find_packages(),
    package_dir={'ghia': 'ghia'},
    package_data={'ghia': ['templates/*.html', 'static/*.*', 'flask_config.json']},
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Environment :: Console',
        'Environment :: Web Environment',
        'Framework :: Flask',
        'Topic :: Software Development :: Bug Tracking',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: GNU General Public License v3 (GPLv3)',
        'Operating System :: POSIX :: Linux',
        'Programming Language :: Python',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.7',
        ],
    entry_points={
        'console_scripts': [
            'ghia = ghia.ghia_cmd:ghia_cmd',
        ],
    },
    install_requires=['Flask', 'click', 'requests'],
    zip_safe=False,
)