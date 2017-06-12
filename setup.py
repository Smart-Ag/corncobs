from setuptools import setup

setup(name = "corncobs",
    install_requires=['pyserial', 'cobs'],
    setup_requires=['pbr>=1.9', 'setuptools>=17.1','pytest-runner'],
    tests_require=['pytest'],
    pbr=True,
)
