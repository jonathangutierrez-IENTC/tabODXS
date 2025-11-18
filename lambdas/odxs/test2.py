from database_utils import MySQLDB

def main():
    db = MySQLDB(
        user="root",
        password="",
        host="127.0.0.1",
        port=3306,        
        database="olimpo-db"
    )
    db.connect()

    # Run your update
    db.update_tableA_from_tableB_in_batches(batch_size=200)

    db.close()


main()