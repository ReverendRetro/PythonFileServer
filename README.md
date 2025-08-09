# Python File Server

A single-file, cross-platform web application for managing and sharing files. It's built with Python and Flask and requires minimal setup. 
Single Python file, should be universal but I test on Debian so steps are for what I use.

---

## Features

* **User Management:** Secure login system with an initial admin setup. Admins can create/delete users and control directory access.
* **Web-Based File Browser:** A two-pane interface with a collapsible directory tree on the left and a file/folder view on the right.
* **File & Folder Operations:**
    * Upload individual files or entire folders.
    * Download files or entire folders as `.zip` archives.
    * Drag-and-drop support for uploads.
* **Resumable Uploads:** Client-side hashing allows uploads to be resumed if the connection is interrupted.
* **Media Handling:**
    * **Audio:** Stream a wide variety of audio formats (`.mp3`, `.flac`, `.wav`, etc.) in a built-in player.
    * **Video:** Stream common video formats in a new browser tab.
    * **Images:** View images in a popup modal with zoom controls. - WIP
* **Customizable UI:**
    * Toggle between list and icon views.
    * Switch between light and dark themes.

---

## How to Run (Debian/Ubuntu)

1.  **Install Python & venv:**
    ```
    sudo apt update; sudo apt install python3 python3-pip python3-venv -y
    ```

2.  **Create Project and Virtual Environment:**
    Navigate to where you want to store the application (e.g., your home directory), create a project folder, and then create a virtual environment inside it.
    bash
    ### Create a directory for the project
    ```
    mkdir ~/fileserver && cd ~/fileserver
    ```

    ### Create the virtual environment
    ```
    python3 -m venv venv
    ```
   

3.  **Activate the Virtual Environment:**
    Before installing dependencies or running the app, you must activate the environment.
    ```
    source venv/bin/activate
    ```
    Your terminal prompt will change to show `(venv)` at the beginning.

4.  **Create Project Files:**
    * Save the main application code as `main.py` inside your `~/fileserver` directory.
    * Create a file named `requirements.txt` and add the following lines to it:
      ```
      Flask
      Werkzeug
      ```

5.  **Install Dependencies:**
    With the virtual environment active, install the required Python packages from your `requirements.txt` file.
    ```
    pip install -r requirements.txt
    ```

6.  **Run the Server Manually:**
    You can run the server directly to test it.
    ```
    python main.py
    ```

7.  **Access the App:**
    Open a web browser and go to your server's IP address on port 5001 (e.g., `http://SERVER.IP.GOES.HERE:5001`).

---

## Run as a Systemd Service (Optional)

This setup will ensure the file server starts automatically when your server boots up.

1.  **Create the Service File:**
    Create a new service configuration file.
    ```
    sudo nano /etc/systemd/system/fileserver.service
    ```

2.  **Add Configuration:**
    Paste the following content into the file. **Important:** Replace `YOUR_USERNAME` with your actual username.

    ```ini
    [Unit]
    Description=Python File Server
    After=network.target

    [Service]
    User=YOUR_USERNAME
    Group=YOUR_USERNAME
    WorkingDirectory=/home/YOUR_USERNAME/fileserver
    ExecStart=/home/YOUR_USERNAME/fileserver/venv/bin/python main.py
    Restart=always

    [Install]
    WantedBy=multi-user.target
    ```

3.  **Reload, Enable, and Start the Service:**
    Run the following commands to enable and start the new service.
    
    ### Reload the systemd daemon to recognize the new file
    ```
    sudo systemctl daemon-reload
    ```

    ### Enable the service to start on boot
    ```
    sudo systemctl enable fileserver.service
    ```

    ### Start the service immediately
    ```
    sudo systemctl start fileserver.service
    ```
    

5.  **Check the Status:**
    You can verify that the service is running correctly with this command:
    ```
    sudo systemctl status fileserver.service
    ```

