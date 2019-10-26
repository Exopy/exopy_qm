def get_directory_from_path(path_to_file):
    split_index = path_to_file.rfind(get_file_separator(path_to_file))
    return path_to_file[:split_index]


def get_file_name_from_path(path_to_file):
    split_index = path_to_file.rfind(get_file_separator(path_to_file))
    return path_to_file[split_index + 1:]


def get_module_name_from_path(path_to_file):
    file_name = get_file_name_from_path(path_to_file)
    return file_name[:file_name.rfind('.')]


def get_file_separator(path_to_file):
    import os
    if os.sep in path_to_file:
        return os.sep
    elif os.altsep in path_to_file:
        return os.altsep

    raise FileNotFoundError()
