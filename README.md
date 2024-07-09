# SQLFTPBackup

SQLFTPBackup is a Python script designed to automate the backup of MySQL databases. It supports storing backups locally, uploading them to an FTP server, and sending email notifications in case of failures. The script can be scheduled to run daily or at specified intervals.

## Features

- Backup MySQL databases
- Upload backups to an FTP server
- Send email notifications on backup failures
- Retain backups locally and on the FTP server for a specified number of days
- Schedule backups daily or at custom intervals
- Log errors and information to a log file

## Requirements

- Python 3.8+
- MySQL server
- FTP server
- Email server

## Installation

1. Clone the repository:

    ```sh
    git clone https://github.com/h-haghpanah/sql_ftp_backup.git
    cd sql_ftp_backup
    ```

2. Install the required packages:

    ```sh
    pip install -r requirements.txt
    ```

3. Create a `.env` file in the project root directory with the following variables:

    ```sh
    MYSQL_USER=your_mysql_username
    MYSQL_PASSWORD=your_mysql_password
    MYSQL_HOST=localhost
    BACKUP_DIR=/path/to/backup/dir
    FTP_SERVER=your_ftp_server
    FTP_PORT=21
    FTP_USER=your_ftp_username
    FTP_PASSWORD=your_ftp_password
    FTP_UPLOAD_PATH=/path/to/upload
    EMAIL_NOTIFICATION_ENABLED=True
    EMAIL_SENDER=your_email_sender@example.com
    EMAIL_RECEIVER=your_email_receiver@example.com
    SMTP_SERVER=smtp.example.com
    SMTP_PORT=587
    SMTP_USER=your_smtp_username
    SMTP_PASSWORD=your_smtp_password
    FAILED_BACKUP_EMAIL_SUBJECT=Backup Error Notification
    LOCAL_RETENTION_DAYS=180
    FTP_RETENTION_DAYS=180
    DAILY_BACKUP_TIME=20:00
    BACKUP_INTERVAL_SECONDS=3600
    BACKUP_TYPE=daily
    FTP_UPLOAD_ENABLED=True
    ```

## Configuration

- `MYSQL_USER`, `MYSQL_PASSWORD`, `MYSQL_HOST`: MySQL database credentials.
- `BACKUP_DIR`: Local directory to store backups.
- `FTP_SERVER`, `FTP_PORT`, `FTP_USER`, `FTP_PASSWORD`, `FTP_UPLOAD_PATH`: FTP server details for uploading backups.
- `EMAIL_SENDER`, `EMAIL_RECEIVER`, `SMTP_SERVER`, `SMTP_PORT`, `SMTP_USER`, `SMTP_PASSWORD`: Email configuration for sending error notifications.
- `FAILED_BACKUP_EMAIL_SUBJECT`: Subject line for error notification emails.
- `LOCAL_RETENTION_DAYS`: Number of days to retain local backups.
- `FTP_RETENTION_DAYS`: Number of days to retain backups on the FTP server.
- `DAILY_BACKUP_TIME`: Time for daily backups (24-hour format).
- `BACKUP_INTERVAL_SECONDS`: Interval (in seconds) between backups when using interval scheduling.
- `BACKUP_TYPE`: Type of backup scheduling (`daily` or `interval`).
- `FTP_UPLOAD_ENABLED`: Boolean to enable/disable FTP upload.
- `EMAIL_NOTIFICATION_ENABLED`: Boolean to enable/disable Email Notification.

## Usage

1. Run the script:

    ```sh
    python sql_ftp_backup.py
    ```

2. The script will schedule backups based on the `BACKUP_TYPE`:

    - **Daily**: Runs at the specified time (`DAILY_BACKUP_TIME`).
    - **Interval**: Runs at the specified interval (`BACKUP_INTERVAL_SECONDS`).

## Backup Types and Options

- **Daily Backup**: This option schedules the backup to run once a day at a specified time. Set `BACKUP_TYPE=daily` and specify the time using `DAILY_BACKUP_TIME` (e.g., `20:00` for 8 PM).
  
  Example:
  ```sh
  BACKUP_TYPE=daily
  DAILY_BACKUP_TIME=20:00
  ```

- **interval Backup**: This option schedules the backup to run at regular intervals, specified in seconds. Set BACKUP_TYPE=interval and specify the interval using BACKUP_INTERVAL_SECONDS (e.g., 3600 for one hour).
  
  Example:
  ```sh
  BACKUP_TYPE=interval
  BACKUP_INTERVAL_SECONDS=3600
  ```
