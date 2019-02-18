from setuptools import setup, find_packages

# from dtk.post_install import setup_post


# class PostInstallCommand(install):
#     """Post-installation for installation mode."""
#
#     def run(self):
#         print('PostInstallCommand.run got called.')
#         # check_call("python post-install.py".split())
#         # check_call("dtksetup post".split())
#         # setup_post()
#         install.run(self)
#         # setup_post()
#         atexit.register(setup_post)

setup(name='dtk-tools',
      version='v1.0.0',
      description='Facilitating submission and analysis of simulations',
      url='https://github.com/InstituteforDiseaseModeling/dtk-tools',
      author='Edward Wenger,'
             'Benoit Raybaud,'
             'Daniel Klein,'
             'Jaline Gerardin,'
             'Milen Nikolov,'
             'Aaron Roney,'
             'Zhaowei Du,'
             'Prashanth Selvaraj'
             'Clark Kirkman IV',
      author_email='ewenger@idmod.org,'
                   'braybaud@idmod.org,'
                   'dklein@idmod.org,'
                   'jgerardin@idmod.org,'
                   'mnikolov@idmod.org,'
                   'aroney@idmod.org,'
                   'zdu@idmod.org,'
                   'pselvaraj@idmod.org'
                   'ckirkman@idmod.org',
      packages=find_packages(),
      install_requires=[
          'six',
          'requests',
          'diskcache',
          'github3.py>=1.0.0a4',
          'numpy==1.14.6',
          'packaging',
          'python-snappy==0.5.2',
          'pyCOMPS==2.3.1',
          'catalyst-report',
          'matplotlib>=2.1.2',
          'scipy>=1.0.0',
          'pandas==0.23.3',
          'psutil>=5.4.3',
          'lz4>=0.21.6',
          'seaborn==0.8.1',
          'statsmodels==0.8.0',
          'SQLAlchemy==1.2.4',
          'monotonic',
          'fasteners==0.14.1',
          'validators',
          'networkx',
          'patsy',
          'astor',
          'openpyxl>=2.5.3',
          'sklearn>=0.0',
          'geopy'],
      setup_requires = ['numpy==1.14.6'],
      # install_requires=[],
      dependency_links=['https://packages.idmod.org/api/pypi/idm-pypi-production/simple'],
      # cmdclass={
      #    'install': PostInstallCommand
      # },
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
