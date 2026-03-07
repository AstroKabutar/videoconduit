# Just for testing purposes

import boto3

# Hardcoded DynamoDB table name
TABLE_NAME = 'videoconduit_database'

# Initialize DynamoDB resource (assumes credentials are set up in environment)
dynamodb = boto3.resource('dynamodb')
table = dynamodb.Table(TABLE_NAME)

def insert_item():
    # Example item to insert
    item = {
        'email': '123@456.com',       # Primary key, must exist in your table definition
        'name': 'Mlice',
        'age': 300
    }
    try:
        table.put_item(Item=item)
        print(f"Inserted item: {item}")
    except Exception as e:
        print(f"Error inserting item: {e}")

def read_item(item_id):
    try:
        response = table.get_item(Key={'id': item_id})
        item = response.get('Item')
        if item:
            print(f"Read item: {item}")
        else:
            print(f"No item found with id: {item_id}")
    except Exception as e:
        print(f"Error reading item: {e}")

if __name__ == "__main__":
    insert_item()

    # Minimal example to get item using both partition (email) and sort (name) keys
    def get_item_by_keys(email, name):
        try:
            response = table.get_item(Key={'email': email, 'name': name})
            item = response.get('Item')
            if item:
                print(f"Item found: {item}")
            else:
                print(f"No item found with email: {email} and name: {name}")
        except Exception as e:
            print(f"Error fetching item: {e}")

    # Fetch an item using primary keys
    get_item_by_keys('123@456.com', 'Mlice')