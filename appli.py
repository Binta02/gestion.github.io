import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import csv
import requests
from bs4 import BeautifulSoup
import re
from googlesearch import search
from flask import Flask, render_template, request
import mysql.connector

app = Flask(__name__)


def send_email(sender_email, receiver_email, subject, message, csv_file_path):
    smtp_server = "smtp.sendgrid.net"
    smtp_port = 587
    username = "apikey"
    password = "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"

    msg = MIMEMultipart()
    msg["From"] = sender_email
    msg["To"] = receiver_email
    msg["Subject"] = subject

    msg.attach(MIMEText(message, "plain"))

    # Joindre le fichier CSV
    with open(csv_file_path, "r", encoding="utf-8") as csv_file:
        csv_data = MIMEText(csv_file.read(), "csv")
        csv_data.add_header(
            "Content-Disposition", "attachment", filename="resultat.csv"
        )

    msg.attach(csv_data)

    try:
        server = smtplib.SMTP(smtp_server, smtp_port)
        server.starttls()
        server.login(username, password)
        server.sendmail(sender_email, receiver_email, msg.as_string())
        server.quit()
        print("E-mail envoyé avec succès !")
    except Exception as e:
        print(f"Erreur lors de l'envoi de l'e-mail : {e}")


def tabToCSV(url, email, phone):
    return f"{url},{email},{phone}"


def contains_phone(text):
    return list(
        set(
            re.findall(
                r"\+?\d{1,2}[-.\s]?\(?\d{2,3}\)?[-.\s]?\d{2,4}[-.\s]?\d{2,4}[-.\s]?\d{2,9}",
                text,
            )
        )
    )


def contains_mail(text):
    a = list(
        set(re.findall(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b", text))
    )
    for elem in a:
        if (
            "node" in elem
            or "bootstrap" in elem
            or len(elem) > 40
            or "js" in elem
            or "png" in elem
            or "cookie" in elem
        ):
            a.remove(elem)
    return a


def google_search(query, num_results):
    results = []
    for url in search(query, num_results=num_results):
        results.append(url)
    return results


@app.route("/")
def index():
    return render_template("form.html")


@app.route("/submit", methods=["POST"])
def submit():
    sender_email = "gestiondeprojetapplication@gmail.com"
    metier = request.form.get("metier")
    localisation = request.form.get("localisation")
    nombre_adresse = int(request.form.get("adresse_recherche"))
    user_email = request.form.get("mail")

    # Connexion à la base de données
    db_connection = mysql.connector.connect(
        host="localhost", user="root", password="", database="entreprise"
    )

    # Insérer les données dans la base de données
    db_cursor = db_connection.cursor()
    query = "INSERT INTO entreprise (Metier, Localisation, Nombre_adresse_recherche) VALUES (%s, %s, %s)"
    values = (metier, localisation, nombre_adresse)
    db_cursor.execute(query, values)
    # Valider la transaction
    db_connection.commit()

    # Récupérer l'ID de la dernière insertion
    entreprise_id = db_cursor.lastrowid

    query = metier + " " + localisation
    search_results = google_search(query, nombre_adresse)

    result_csv = ""

    if search_results:
        for url in search_results:
            try:
                response = requests.get(url)
                soup = BeautifulSoup(response.text, "html.parser")
                emails = contains_mail(str(soup))
                emails_str = ",".join(emails)
                phones = contains_phone(str(soup))
                phones_str = ",".join(phones)
                result_csv += tabToCSV(url, emails_str, phones_str) + "\n"
            except Exception as e:
                print(f"Error processing URL {url}: {e}")

    csv_file_path = "resultat.csv"
    result_csv_header = "URL,Emails,Téléphones\n"

    with open(csv_file_path, "w", encoding="utf-8") as csv_file:
        csv_file.write(result_csv_header)
        csv_file.write(result_csv)

    # Mettre à jour la colonne Resultat_CSV dans la base de données
    db_cursor.execute(
        "UPDATE entreprise SET Resultat_CSV = %s WHERE id_entreprise = %s",
        (result_csv, entreprise_id),
    )
    db_connection.commit()

    # Fermer la connexion à la base de données
    db_cursor.close()
    db_connection.close()

    email_subject = "Résultats de recherche d'entreprises"
    email_message = "Veuillez trouver ci-joint le fichier CSV contenant les résultats de votre recherche d'entreprises."
    send_email(sender_email, user_email, email_subject, email_message, csv_file_path)

    return "Formulaire soumis avec succès !"


if __name__ == "__main__":
    app.run()
