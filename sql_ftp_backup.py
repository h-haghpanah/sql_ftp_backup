import os
import subprocess
import ftplib
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import datetime
from decouple import config
import mysql.connector
import shutil
import schedule
import time
import logging
import traceback
import gzip


class SQLFTPBackup:
    def __init__(self):
        self.MYSQL_USER = config("MYSQL_USER")
        self.MYSQL_PASSWORD = config("MYSQL_PASSWORD")
        self.MYSQL_HOST = config("MYSQL_HOST", default="localhost")
        self.BACKUP_DIR = config("BACKUP_DIR")
        self.FTP_SERVER = config("FTP_SERVER")
        self.FTP_PORT = config("FTP_PORT", cast=int)
        self.FTP_USER = config("FTP_USER")
        self.FTP_PASSWORD = config("FTP_PASSWORD")
        self.FTP_UPLOAD_PATH = config("FTP_UPLOAD_PATH")
        self.EMAIL_NOTIFICATION_ENABLED = config("EMAIL_NOTIFICATION_ENABLED", cast=bool, default=False)
        self.EMAIL_SENDER = config("EMAIL_SENDER")
        self.EMAIL_RECEIVER = config("EMAIL_RECEIVER")
        self.SMTP_SERVER = config("SMTP_SERVER")
        self.SMTP_PORT = config("SMTP_PORT", cast=int)
        self.SMTP_USER = config("SMTP_USER")
        self.SMTP_PASSWORD = config("SMTP_PASSWORD")
        self.FAILED_BACKUP_EMAIL_SUBJECT = config("FAILED_BACKUP_EMAIL_SUBJECT", cast=str, default="Backup Error Notification")
        self.LOCAL_RETENTION_DAYS = config("LOCAL_RETENTION_DAYS", cast=int, default=180)
        self.FTP_RETENTION_DAYS = config("FTP_RETENTION_DAYS", cast=int, default=180)
        self.DAILY_BACKUP_TIME = config("DAILY_BACKUP_TIME", default="20:00")
        self.BACKUP_INTERVAL_SECONDS = config("BACKUP_INTERVAL_SECONDS", cast=int, default=3600)
        self.LAST_BACKUP_FILE = os.path.join(self.BACKUP_DIR, 'last_backup.txt')
        self.BACKUP_TYPE = config("BACKUP_TYPE", default="daily")  # 'daily' or 'interval'
        self.FTP_UPLOAD_ENABLED = config("FTP_UPLOAD_ENABLED", cast=bool, default=False)
        self.log_file = LogFile()
        self.compress_backup = config("COMPRESS_BACKUP", cast=bool, default=False)
        self.keep_orginal_file = config("KEEP_ORGINAL_FILE", cast=bool, default=True)
        self.keep_orginal_file_every_x_time_backup = config("KEEP_ORGINAL_FILE_EVERY_X_TIME_BACKUP", cast=int, default=1)
        self.x_time_backup = 1

    def get_database_list(self):
        try:
            connection = mysql.connector.connect(
                host=self.MYSQL_HOST,
                user=self.MYSQL_USER,
                password=self.MYSQL_PASSWORD
            )
            cursor = connection.cursor()
            cursor.execute("SHOW DATABASES")
            databases = [db[0] for db in cursor.fetchall() if db[0] not in ('information_schema', 'performance_schema', 'mysql', 'sys')]
            connection.close()
            return databases
        except Exception as e:
            error = f"Failed to retrieve database list: {str(e)}"
            if self.EMAIL_NOTIFICATION_ENABLED:
                self.notify_error(error)
            self.log_file.error(traceback.format_exc(), error)

    def backup_database(self, database_name, backup_dir):
        try:
            timestamp = datetime.datetime.now().strftime('%Y-%m-%d_%H_%M')
            backup_file = os.path.join(backup_dir, f"{database_name}_{timestamp}.sql")

            dump_command = f"mysqldump -u {self.MYSQL_USER} -p{self.MYSQL_PASSWORD} {database_name} > {backup_file}"
            subprocess.check_call(dump_command, shell=True)
            if self.compress_backup:
                compressed_file = f"{backup_file}.gz"
                with open(backup_file, 'rb') as f_in:
                    with gzip.open(compressed_file, 'wb') as f_out:
                        shutil.copyfileobj(f_in, f_out)
                if self.keep_orginal_file:
                    if self.keep_orginal_file_every_x_time_backup == 0:
                        return [backup_file, compressed_file]
                    else:
                        if self.x_time_backup >= self.keep_orginal_file_every_x_time_backup:
                            return [backup_file, compressed_file]
                        else:
                            os.remove(backup_file)
                            return [compressed_file]
                else:
                    os.remove(backup_file)
                    return [compressed_file]
            else:
                return [backup_file]

        except Exception as e:
            error = f"Backup failed for database {database_name}: {str(e)}"
            if self.EMAIL_NOTIFICATION_ENABLED:
                self.notify_error(error)
            self.log_file.error(traceback.format_exc(), error)

    def upload_to_ftp(self, file_path, ftp_folder):
        try:
            with ftplib.FTP() as ftp:
                ftp.connect(self.FTP_SERVER, self.FTP_PORT)
                ftp.login(self.FTP_USER, self.FTP_PASSWORD)
                ftp.cwd(self.FTP_UPLOAD_PATH)

                # Check if the ftp_folder exists, if not create it
                try:
                    if ftp_folder not in ftp.nlst():
                        ftp.mkd(ftp_folder)
                except ftplib.error_perm as e:
                    if str(e).startswith('550'):
                        try:
                            ftp.mkd(ftp_folder)
                        except Exception as e:
                            error = f"Faild to create folder in FTP: {str(e)}"
                            self.log_file.error(traceback.format_exc(), error)
                    else:
                        error = f"Faild to create folder in FTP: {str(e)}"
                        self.log_file.error(traceback.format_exc(), error)
                upload_path = f"{self.FTP_UPLOAD_PATH}/{ftp_folder}"
                ftp.cwd(upload_path)

                with open(file_path, 'rb') as file:
                    ftp.storbinary(f'STOR {os.path.basename(file_path)}', file)
                print(f"Upload successful: {file_path} uploaded to {upload_path}")
        except Exception as e:
            error = f"FTP upload failed for {file_path}: {str(e)}"
            if self.EMAIL_NOTIFICATION_ENABLED:
                self.notify_error(error)
            self.log_file.error(traceback.format_exc(), error)

    def notify_error(self, message):
        try:
            msg = MIMEMultipart()
            msg['From'] = self.EMAIL_SENDER
            msg['To'] = self.EMAIL_RECEIVER
            msg['Subject'] = self.FAILED_BACKUP_EMAIL_SUBJECT

            body = MIMEText(message, 'plain')
            msg.attach(body)

            with smtplib.SMTP(self.SMTP_SERVER, self.SMTP_PORT) as server:
                server.starttls()
                server.login(self.SMTP_USER, self.SMTP_PASSWORD)
                server.sendmail(self.EMAIL_SENDER, self.EMAIL_RECEIVER, msg.as_string())
        except Exception as e:
            error = f"Failed to send error email: {str(e)}"
            self.log_file.error(traceback.format_exc(), error)

    def delete_old_local_backups(self):
        now = datetime.datetime.now()
        try:
            cutoff_date = now - datetime.timedelta(days=self.LOCAL_RETENTION_DAYS)
            for root, dirs, files in os.walk(self.BACKUP_DIR):
                for dir_name in dirs:
                    dir_path = os.path.join(root, dir_name)
                    try:
                        dir_date = datetime.datetime.strptime(dir_name, '%Y-%m-%d')
                        if dir_date < cutoff_date:
                            shutil.rmtree(dir_path)
                            print(f"Deleted old backup folder: {dir_path}")
                    except ValueError:
                        # Skip folders that don't match the date format
                        continue
        except Exception as e:
            error = f"Failed to delete old backups from local: {str(e)}"
            if self.EMAIL_NOTIFICATION_ENABLED:
                self.notify_error(error)
            self.log_file.error(traceback.format_exc(), f"Failed to delete old backups: {str(e)}")

    def delete_old_ftp_backups(self):
        now = datetime.datetime.now()
        try:
            cutoff_date = now - datetime.timedelta(days=self.FTP_RETENTION_DAYS)
            with ftplib.FTP() as ftp:
                ftp.connect(self.FTP_SERVER, self.FTP_PORT)
                ftp.login(self.FTP_USER, self.FTP_PASSWORD)
                ftp.cwd(self.FTP_UPLOAD_PATH)

                folders = ftp.nlst()

                for folder in folders:
                    try:
                        folder_date = datetime.datetime.strptime(folder, '%Y-%m-%d')
                        if folder_date < cutoff_date:
                            folder_path = f"{self.FTP_UPLOAD_PATH}/{folder}"
                            ftp.cwd(folder_path)
                            files = ftp.nlst()
                            for file in files:
                                try:
                                    ftp.delete(file)
                                except ftplib.error_perm:
                                    self._delete_ftp_folder(ftp, f"{folder_path}/{file}")
                            ftp.cwd('..')
                            ftp.rmd(folder_path)
                            print(f"Deleted old backup folder: {folder_path}")
                    except ValueError:
                        # Skip folders that don't match the date format
                        continue
        except Exception as e:
            error = f"Failed to delete old backups from ftp: {str(e)}"
            if self.EMAIL_NOTIFICATION_ENABLED:
                self.notify_error(error)
            self.log_file.error(traceback.format_exc(), error)

    def save_last_backup_time(self):
        with open(self.LAST_BACKUP_FILE, 'w') as f:
            f.write(datetime.datetime.now().isoformat())

    def load_last_backup_time(self):
        if os.path.exists(self.LAST_BACKUP_FILE):
            with open(self.LAST_BACKUP_FILE, 'r') as f:
                return datetime.datetime.fromisoformat(f.read().strip())
        return None

    def run_backup(self):
        try:
            date_str = datetime.datetime.now().strftime('%Y-%m-%d')
            full_date_str = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            backup_date_dir = os.path.join(self.BACKUP_DIR, date_str)
            os.makedirs(backup_date_dir, exist_ok=True)

            databases = self.get_database_list()
            databases = [databases[0]]
            for db in databases:
                backup_file = self.backup_database(db, backup_date_dir)
                if self.FTP_UPLOAD_ENABLED:
                    ftp_folder = date_str
                    for bak in backup_file:
                        self.upload_to_ftp(bak, ftp_folder)
            if self.FTP_UPLOAD_ENABLED:
                self.delete_old_ftp_backups()
            self.delete_old_local_backups()
            self.save_last_backup_time()
            self.log_file.info(f"Backup successfull at {full_date_str}")
            if self.x_time_backup >= self.keep_orginal_file_every_x_time_backup:
                self.x_time_backup = 1
            else:
                self.x_time_backup += 1
        except Exception as e:
            error = f"An error occurred: {str(e)}"
            if self.EMAIL_NOTIFICATION_ENABLED:
                self.notify_error(error)
            self.log_file.error(traceback.format_exc(), error)

    def schedule_backup(self):
        if self.BACKUP_TYPE == 'daily':
            # Schedule daily backup at specified time
            schedule.every().day.at(self.DAILY_BACKUP_TIME).do(self.run_backup)
        elif self.BACKUP_TYPE == 'interval':
            # Schedule interval backup based on last backup time
            schedule.every(self.BACKUP_INTERVAL_SECONDS).seconds.do(self.run_backup)

        while True:
            schedule.run_pending()
            time.sleep(60)


class LogFile:
    def __init__(self):
        self.logger = logging.getLogger(__name__)

        # Check if a FileHandler is already present
        file_handler_present = any(isinstance(handler, logging.FileHandler) for handler in self.logger.handlers)

        # Only add the FileHandler if it's not already present
        if not file_handler_present:
            f_handler = logging.FileHandler("messages.log", encoding='utf-8')
            f_handler.setLevel(logging.ERROR)
            f_format = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
            f_handler.setFormatter(f_format)
            self.logger.addHandler(f_handler)

    def error(self, trace, e):
        print(e)
        self.logger.error(trace + str(e))

    def warning(self, w):
        self.logger.warning(w)

    def info(self, i):
        self.logger.info(i)


if __name__ == "__main__":
    backup = SQLFTPBackup()
    backup.schedule_backup()
