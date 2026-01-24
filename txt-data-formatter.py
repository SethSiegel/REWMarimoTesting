#! python3

# This program takes in the sine test data from REW and returns the data in
# a usable format

import os


def get_folder_size(folder_path):
    '''Returns the number of files, folders, and the names of the folders
    in the given folder path.


    Args:
        folder_path (str): The path to the folder to be checked.


    Returns:
        file_count (int): The number of files in the folder.
        folder_count (int): The number of folders in the folder.
        folder_names (list): The names of the folders in the folder.
    '''

    file_count = 0
    folder_names = []
    for entry in os.scandir(folder_path):
        if entry.is_file():
            file_count += 1
        elif entry.is_dir():
            folder_names.append(entry.name)
    folder_count = len(folder_names)
    return file_count, folder_count, folder_names


def strip_file(in_file_path, out_file_path):
    '''Strips every line that beigns with an asterisk (*) from the input file
    and writes the remaining lines to the output file.


    Args:
        in_file_path (str): The path to the input file.
        out_file_path (str): The path to the output file.


    Returns:
        data (list): The data that is left from stripping the input file.
    '''
    with open(in_file_path, 'r') as file:
        data = file.readlines()

    filtered_lines = [line for line in data if not line.
                      lstrip().startswith('*')]

    with open(out_file_path, 'w') as file:
        file.writelines(filtered_lines)

    return data


def get_all_raw_file_names(folder_path):
    '''Returns a list of all raw file names in the given folder path.


    Args:
        folder_path (str): The path to the folder to be checked.


    Returns:
        all_files (list): A list of all raw file names in the folder.
    '''
    all_files = []
    for dirpath, dirnames, filenames in os.walk(folder_path):
        for filename in filenames:
            all_files.append(os.path.join(filename))  # full path
            # all_files.append(filename)  # just the file name
    return all_files


def strip_raw_file(raw_folder_path, folder_num=''):
    '''Strips all raw files in the given folder path and writes the
    remaining lines to a new file in a cleaned folder.


    Args:
        raw_folder_path (str): The path to the folder containing the raw
                               files.
        folder_num (str): The number of the folder containing the raw files.
                          Defaults to ''.


    Returns:
        N/A
    '''
    for dirpath, dirnames, filenames in os.walk(raw_folder_path):
        for filename in filenames:
            out_file_path = os.path.join(
                dirpath.replace('-raw', '-cleaned'),
                filename.replace('.txt', '-cleaned.txt'))
            strip_file(f'{folder_num}/{filename}',
                       out_file_path),


def get_raw_folders(folder_path):
    '''Returns a list of all raw folders in the given folder path.


    Args:
        folder_path (str): The path to the folder to be checked.


    Returns:
        raw_folders (list): A list of all raw folders in the folder.
    '''
    raw_folders = []
    for dirpath, dirnames, filenames in os.walk(folder_path):
        for dirname in dirnames:
            if '-raw' in dirname:
                raw_folders.append(os.path.normpath(os.path.join(dirpath,
                                                                 dirname)))
    return raw_folders


folder_path = './amp-data'
# print(get_folder_size('./amp-data/amp3-cleaned'))
numFiles, numFolders, folder_names = get_folder_size(folder_path)
print(numFiles, numFolders, folder_names)
raw_folders = get_raw_folders(folder_path)
print(raw_folders)
for i in range(len(raw_folders)):
    raw_folder = raw_folders[i].split('/')[-1]
    print(raw_folder)
    strip_raw_file(raw_folders[i], raw_folder)
