from dynaconf import settings
from javascript_data_files import read_js, write_js


# Replace the get_data_source function with dynaconf configuration
def get_data_source():
    return settings.DATA_SOURCE


def get_data():
    return read_js(get_data_source(), varname="bookmarks")


def write_data(data):
    write_js(get_data_source(), value=list(data), varname="bookmarks")
