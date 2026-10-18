from flask import Flask, render_template
from database import get_db_connection

app = Flask(__name__)


@app.route('/')
def dashboard():

    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)

    cursor.execute("SELECT COUNT(*) AS total FROM companies")
    result = cursor.fetchone()

    cursor.close()
    connection.close()

    return render_template(
        'dashboard.html',
        total_companies=result['total']
    )


if __name__ == '__main__':
    app.run(debug=True)