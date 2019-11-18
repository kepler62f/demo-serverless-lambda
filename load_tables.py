from string import digits


import os
import pymysql.cursors
import re
import requests
import sys
import zipfile


def download_zip(url):
    """
    Download file from URL
    """
    try:
        response = requests.get(
            url,
            allow_redirects=True
        )
        if response.raise_for_status() is None:
            zipfilename = get_filename(response.headers.get('content-disposition'))
            zipfilepath = '/tmp/' + zipfilename
            with open(zipfilepath, 'wb') as f:
                f.write(response.content)
            return zipfilename
    except Exception as e:
        print('Error downloading from file:')
        print(e)
        sys.exit(1)
    return ''


def extract_zip(filename):
    extracted_files_path = '/tmp/'+filename.replace('.zip', '')
    if not os.path.exists(extracted_files_path):
        os.makedirs(extracted_files_path)
    with zipfile.ZipFile('/tmp/'+filename, 'r') as f:
        f.extractall(extracted_files_path)


def get_filename(header):
    """
    Get filename from content-disposition header
    """
    if not header:
        return None
    name = re.findall('filename=(.+)', header)
    if len(name) == 0:
        return None
    return name[0].strip('\"')  # In test cases, I discover filename returns leading & trailing double quotes


def parse_sql(filename):
    """
    Source: http://adamlamers.com/post/GRBJUKCDMPOA
    """
    data = open(filename, 'r').readlines()
    stmts = []
    DELIMITER = ';'
    stmt = ''

    for lineno, line in enumerate(data):
        if not line.strip():
            continue

        if line.startswith('--'):
            continue

        if 'DELIMITER' in line:
            DELIMITER = line.split()[1]
            continue

        if (DELIMITER not in line):
            stmt += line.replace(DELIMITER, ';')
            continue

        if stmt:
            stmt += line
            stmts.append(stmt.strip())
            stmt = ''
        else:
            stmts.append(line.strip())
    return stmts


def get_db_connection():
    return pymysql.connect(
        host=os.environ['DB_HOST'],
        user=os.environ['DB_USER'],
        password=os.environ['DB_P'],
        db=os.environ['DB_NAME'],
        cursorclass=pymysql.cursors.DictCursor
    )


def execute_sql(conn, statements):
    try:
        with conn.cursor() as cursor:
            for statement in statements:
                cursor.execute(statement)
            conn.commit()
        return None
    except Exception as e:
        return {'error_msg': e}


def lambda_handler(event, context):
    url = os.environ['DOWNLOAD_URL']
    zipfilename = ''
    zipfilepath = ''
    extracted_files_path = ''
    sql_error_list = []

    zipfilename = download_zip(url)

    if zipfilename == '':
        exit(1)

    extract_zip(zipfilename)

    # Assumed that zip file directory structure is consistent
    final_extract_path = '/tmp/'+zipfilename.replace('.zip', '')+'/'+zipfilename.replace('.zip', '')

    db_conn = get_db_connection()

    # Temporarily turn off foreign key check for recreating table
    # https://stackoverflow.com/questions/11100911/cant-drop-table-a-foreign-key-constraint-fails
    drop_table = ["SET FOREIGN_KEY_CHECKS=0;", "DROP TABLE {};", "SET FOREIGN_KEY_CHECKS=1;"]

    # Process each sql script
    for dirpath, _, filenames in os.walk(final_extract_path):
        for f in sorted(filenames):  # must be sorted due to dependencies of table keys
            if f.endswith('.sql'):

                # Drop existing table
                table_name = f.replace('.sql', '').lstrip(digits).lstrip('_')  # remove .sql, then strip leading digits and _

                drop_sql = [drop_table[0], drop_table[1].format(table_name), drop_table[2]]
                err = execute_sql(db_conn, drop_sql)
                err = None

                # Run script
                path = os.path.abspath(os.path.join(dirpath, f))
                statements = parse_sql(path)
                err = execute_sql(db_conn, statements)

                # Push to error list if sql write encounters error,
                # no action taken on list for now, but can be used for
                # error tracking in the future
                if err is not None:
                    sql_error_list.append({'filename': f, 'error': err['error_msg']})