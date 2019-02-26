from setuptools import setup, find_packages
from dtk import __version__ as DTK_VERSION

setup(name='dtk-tools',
      version=DTK_VERSION,
      description='Facilitating submission and analysis of simulations',
      url='https://github.com/InstituteforDiseaseModeling/dtk-tools',
      author='Edward Wenger,'
             'Benoit Raybaud,'
             'Daniel Klein,'
             'Jaline Gerardin,'
             'Milen Nikolov,'
             'Clinton Collins,'
             'Zhaowei Du,'
             'Prashanth Selvaraj,'
             'Clark Kirkman IV',
      author_email='ewenger@idmod.org,'
                   'braybaud@idmod.org,'
                   'dklein@idmod.org,'
                   'jgerardin@idmod.org,'
                   'mnikolov@idmod.org,'
                   'ccollins@idmod.org,'
                   'zdu@idmod.org,'
                   'pselvaraj@idmod.org,'
                   'ckirkman@idmod.org',
      packages=find_packages(),
      install_requires=[
          'six',
          'requests',
          'diskcache',
          'github3.py>=1.0.0a4',
          'numpy==1.16.1',
          'packaging',
          'python-snappy==0.5.3',
          'pyCOMPS==2.3.1',
          'catalyst-report',
          'matplotlib>=2.1.2',
          'scipy>=1.0.0',
          'pandas==0.23.3',
          'psutil>=5.4.3',
          'lz4>=0.21.6',
          'seaborn==0.8.1',
          'statsmodels==0.9.0',
          'SQLAlchemy==1.2.4',
          'monotonic',
          'fasteners==0.14.1',
          'validators',
          'networkx',
          'patsy',
          'astor',
          'openpyxl>=2.5.3',
          'geopy'],
      dependency_links=['https://packages.idmod.org/api/pypi/idm-pypi-production/simple'],
      entry_points={
          'console_scripts': ['calibtool = calibtool.commands:main', 'dtk = dtk.commands:main',
                              'dtksetup = dtk.post_install:main']
      },
      package_data={
          '': ['*.ini', '*.json', '*.csv', '*.bin', '*.emodl', '*.exe', '*.dll', '*.xml', '*.sls', '*.ss', '*.txt'],
          'simtools': ['*.ini', '*.json'],
          'dtk': ['*.ini'],
          'examples': ['inputs/*.exe', 'inputs/dlls/reporter_plugins/*.dll']
      },
      zip_safe=False)
