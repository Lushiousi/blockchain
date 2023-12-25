from flask import Flask, render_template, redirect, request, flash, url_for, session
import json
from contract import contract, w3

app = Flask(__name__)
app.secret_key = "123"

def set_current_user_address(address):
    session['current_user_address'] = address

def get_current_user_address():
    return session.get('current_user_address', None)

@app.route("/", methods=["GET"])
def index():
    return redirect('register')


@app.route("/login", methods=["POST", "GET"])
def login():
    if request.method == "POST":
        try:
            user = request.form["selected_account"]
            password = request.form["password"]
            set_current_user_address(user)
            # Получаем информацию о пользователе из смарт-контракта
            user_info = contract.functions.getUserInfo(user).call()
            # Проверяем правильность пароля и является ли пользователь администратором
            if user_info[0] == password:
                if user_info[1] == False:  # Если пользователь является администратором
                    return redirect('transacts')
                else:
                    flash("Вы успешно вошли в систему", "success")
                    return redirect('admin_panel')
            else:
                flash("Неправильный логин или пароль", "error")
                return render_template("reglog.html", accounts=w3.eth.accounts)
        except Exception as e:
            flash(f"Произошла ошибка: {str(e)}", "error")
            return render_template("reglog.html", accounts=w3.eth.accounts)
    else:
        return render_template("reglog.html", accounts=w3.eth.accounts)



@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "GET":
        try:
            accounts = w3.eth.accounts
            return render_template("reglog.html", accounts=accounts)
        except Exception as e:
            flash(f"Произошла ошибка: {str(e)}", "error")
            return render_template("reglog.html", accounts=[])
    elif request.method == "POST":
        try:
            password = request.form["password"]
            selected_account = request.form["selected_account"]  
            contract.functions.registerUser(selected_account, password).transact({'from': selected_account})  
            flash("Пользователь зарегистрирован успешно", "success")
            print(password)
            return redirect('login')
        except Exception as e:
            flash(f"Произошла ошибка: {str(e)}", "error")
            return render_template("reglog.html", accounts=w3.eth.accounts)

@app.route("/admin_panel")
def admin_panel():
    current_user_address = get_current_user_address()  # Получаем адрес текущего пользователя из сессии
    if current_user_address:
        return render_template("admin_panel.html", current_user=current_user_address)
    else:
        return "Пользователь не авторизован"

@app.route("/nominate_admin", methods=["GET", "POST"])
def nominate_admin():
    if request.method == "POST":
        selected_address = request.form.get("address")  # Получаем выбранный адрес от клиента
        try:
            contract.functions.nominateAdmin(selected_address).transact({'from': w3.eth.accounts[0]})
            flash(f"Пользователь {selected_address} назначен на роль администратора", "success")
        except Exception as e:
            flash(f"Произошла ошибка: {str(e)}", "error")
        return redirect(url_for("admin_panel"))

    address_options = []
    for account in w3.eth.accounts:
        password, is_admin, is_nominated = contract.functions.getUserInfo(account).call()
        if not is_admin:
            address_options.append(account)
            
    return render_template('nominate_admin.html', address_options = address_options)

@app.route("/confirm_admin_nomination", methods=["GET", "POST"])
def confirm_admin_nomination():
    if request.method == "POST":
        address = request.form["address"]
        try:
            contract.functions.confirmAdminNomination(address).transact({'from': w3.eth.accounts[0]})
            flash(f"Назначение пользователя {address} на роль администратора подтверждено", "success")
        except Exception as e:
            flash(f"Произошла ошибка: {str(e)}", "error")
        return redirect(url_for("admin_panel"))

    nominated_users = []
    for account in w3.eth.accounts:
        password, is_admin, is_nominated = contract.functions.getUserInfo(account).call()
        if is_nominated:
            nominated_users.append(account)

    return render_template("confirm_admin.html", nominated_users=nominated_users)

@app.route("/transacts", methods=["GET"])
def trans():
    return render_template('transact.html')

@app.route("/initiate_transfer", methods=["GET","POST"])
def initiate_transfer():
    if request.method == "GET":
        return render_template('initiate_transfer.html')
    elif request.method == "POST":
        _receiver = request.form.get("receiver")
        _amount = int(request.form.get("amount"))
        _amount_eth = w3.to_wei(_amount, 'ether')
        _code_word = request.form.get("code_word")
        try:
            contract.functions.initiateTransfer(_receiver, _amount, _code_word).transact({'from': get_current_user_address(), 'value': _amount})
            flash(f"Transfer initiated successfully with {_amount} wei", "success")
        except Exception as e:
            flash(f"An error occurred: {str(e)}", "error")
        return redirect(url_for("admin_panel"))
        


@app.route("/confirm_transfer", methods=["GET","POST"])
def confirm_transfer():
    if request.method == "GET":
        return render_template('confirm_trans.html')
    elif request.method == "POST":
        _transfer_id = int(request.form.get("transfer_id"))
        _code_word = request.form.get("code_word")
        try:
            w3.eth.default_account = w3.eth.accounts[0]  # Устанавливаем аккаунт по умолчанию для транзакций
            tx_hash = contract.functions.confirmTransfer(_transfer_id, _code_word).transact()
            flash("Transfer confirmed successfully", "success")
        except Exception as e:
            flash(f"An error occurred: {str(e)}", "error")
        return redirect(url_for("admin_panel"))


if __name__ == '__main__':
    app.run(debug=True)