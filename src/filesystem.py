from os import access, R_OK, W_OK
from os.path import isfile, isdir


class Filesystem:

    @staticmethod
    def file_readable(path):
        """Function to check whether a file is readable or not

        Parameters
        ----------
        path
            Path to file

        """
        return isfile(path) and access(path, R_OK)

    def file_writeable(path):
        """Function to check whether a file is writeable or not

        Parameters
        ----------
        path
            Path to file

        """
        return isfile(path) and access(path, W_OK)

    def dir_writeable(path):
        """Function to check whether a directory is writeable or not

        Parameters
        ----------
        path
            Path to file

        """
        return isdir(path) and access(path, W_OK)

    def file_exists(file):
        """Function to check whether a file exists or not

        Parameters
        ----------
        file
            Path to file

        """
        return isfile(file)
