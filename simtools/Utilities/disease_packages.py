# this file contains methods for interfacing with the disease input packages github repository
import subprocess
import os
import zipfile
import uuid
import github3
from simtools.Utilities.General import rmtree_f

PACKAGES_GITHUB_URL = 'https://github.com/InstituteforDiseaseModeling/dtk-packages.git'

def parse_version(tag):
    """
        Converts a disease input package version (tag name) to its package/version components.
        :param tag: A GitHub tag to parse.
        :return: A length 2 list: [PACKAGE_NAME, VERSION_STR]
    """
    return tag.split('-')

def construct_version(disease, ver):
    """
            Constructs a disease input package version (tag name) from package/version components.
            :param disease: The disease/package name to construct a GitHub tag from.
            :param ver: The version of the specified package/disease.
            :return: A len 2 list: PACKAGE_NAME-VERSION_STR
        """
    return '-'.join([disease, ver])

def get_latest_version_for_package(package_name):
    """
        Determines the most recent inputs version for a given disease.
        :param package_name: Looks for a version of this disease/package
        :return: The most recent version string (alphabetically last version).
    """
    versions = get_versions_for_package(package_name)
    if len(versions) == 0:
        version = None
    else:
        version = sorted(versions)[-1]
    return version

# returns True/False if the given inputs package exists in github
def package_exists(package_name):
    """
        Determines if the specified disease inputs package is available, any version.
        :param package_name: This is the disease/package checked.
        :return: True/False
    """
    packages = get_available('branch')
    return packages.__contains__(package_name)

def version_exists_for_package(version, package_name):
    """
        Determines if the specified version of the given disease inputs is available.
        :param version: The version to look for.
        :param package_name: The disease/package to check.
        :return: True/False
    """
    available_versions = get_versions_for_package(package_name)
    return available_versions.__contains__(version)

def get_versions_for_package(package_name):
    """
        Returns the input versions available for the selected disease/package.
        :param package_name: The disease/package to check.
        :return: A list of available versions.
    """
    tags = get_available('tag')
    versions = []
    for tag in tags:
        try:
            disease, version = parse_version(tag)
        except:
            continue  # ignore tags of alternate formats
        if disease == package_name:
            versions.append(version)
    return versions

def get_available(id_type):
    """
        Returns a list of all existing disease input packages (branches) or input versions (tags).
        :param id_type: Determines if branches or tags are listed. Pass 'branch' or 'tag'.
        :return: A list of available input packages or versions.
        :raises: Exception if id_type is not recognized.
    """
    if id_type == 'branch':
        results = [b.name for b in DTKGitHub.repository().iter_branches()]
    elif id_type == 'tag':
        results = [t.name for t in DTKGitHub.repository().iter_tags()]
    else:
        raise Exception('No such git type: %s . Must be branch or tag.' % id_type)
    if id_type == 'branch':
        results.remove('master') # this isn't really something available for use :)
    return results

def get(package, version, dest):
    """
    Obtains the requested disease input package & version and puts it at the desired location.
    :param package: The disease input package to obtain.
    :param version: The version of said package.
    :param dest: The directory to contain obtained inputs.
    :return: Nothing.
    """

    release = construct_version(package, version)
    zip_file = '%s.zip' % release

    # make sure we get a clean copy
    if os.path.exists(zip_file):
        os.remove(zip_file)
    success = DTKGitHub.repository().archive('zipball', path=zip_file, ref=release)
    if not success:
        raise Exception("Failed to download package: %s version: %s from repository." % (package, version))

    zip_ref = None
    try:
        # Unzip
        zip_ref = zipfile.ZipFile(zip_file, 'r')

        # Get the name of the root dir (only one)
        dir = [x for x in zip_ref.namelist() if x.endswith('/') and x.count('/')==1][0]

        try:
            # Extract and move package to desired location
            zip_ref.extractall()
            if os.path.exists(package):
                rmtree_f(package)
            os.rename(dir, package)
        except:
            rmtree_f(dir) # do not leave garbage around
    finally:
        # Always close/delete the zip, successful or not
        if zip_ref:
            zip_ref.close()
        if os.path.exists(zip_file):
            os.remove(zip_file)

class DTKGitHub(object):
    CREDENTIAL_FILE = os.path.join(os.path.expanduser("~"), 'githubcred.txt') # ck4 get rid of credential file
    OWNER = 'InstituteforDiseaseModeling'
    PACKAGE_REPOSITORY = 'dtk-packages'
    DTK_TOOLS_REPOSITORY = 'dtk-tools'

    @classmethod
    def login(cls):
        # Get an authorization token first
        token = cls.retrieve_token()
        cls.session = github3.login(token=token)
        cls.repo = cls.session.repository(cls.OWNER, cls.PACKAGE_REPOSITORY)

    @classmethod
    def repository(cls):
        if not hasattr(cls, 'repo'):
            cls.login()
        return cls.repo

    @classmethod
    def create_token(cls):
        # Asks user for username/password
        user = raw_input("Please enter your GitHub username: ")
        password = raw_input("Please enter your GitHub password: ")

        # Info for the GitHub token
        note = 'dtk-tools-%s' % str(uuid.uuid4())[:4]
        note_url = 'https://github.com/%s/%s' % (cls.OWNER, cls.DTK_TOOLS_REPOSITORY)
        scopes = ['user', 'repo']

        # Authenticate the user and create the token
        auth = github3.authorize(user, password, scopes, note, note_url)

        # Write the info to disk
        with open(cls.CREDENTIAL_FILE, 'w') as fd:
            fd.write(auth.token + '\n')

        return auth.token

    @classmethod
    def retrieve_token(cls):
        if os.path.exists(cls.CREDENTIAL_FILE):
            # The token file exists -> use the token
            with open(cls.CREDENTIAL_FILE, 'r') as fd:
                token = fd.readline().strip()
        else:
            # The token file does not exist -> create a token
            token = cls.create_token()
        return token
# class DTKGitHub
