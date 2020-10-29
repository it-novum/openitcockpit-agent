from os import access, R_OK
from os.path import isfile


class Filesystem:

    @staticmethod
    def file_readable(path):
        """Function to check whether a file is readable or not

        Parameters
        ----------
        path
            Path to file

        """
        return (isfile(path) and access(path, R_OK))
