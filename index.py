import os
import multiprocessing
import time
from flask import Flask, request, jsonify
import subprocess

def run_command(command):
    subprocess.run(command, shell=True, check=True)

def write_file(filename, content):
    with open(filename, 'w') as f:
        f.write(content)

def setup_dns_server():
    # DNS server setup code
    # Update system
    run_command("sudo apt update && sudo apt upgrade -y")

    # Install BIND
    run_command("sudo apt install bind9 bind9utils bind9-doc -y")

    # Configure BIND
    named_conf_options = """options {
        directory "/var/cache/bind";
        recursion yes;
        allow-recursion { localhost; 919.191.9.0/24; };
        listen-on { 127.0.0.1; 919.191.9.9; };
        allow-transfer { none; };
        forwarders {
            8.8.8.8;
            8.8.4.4;
        };
    };"""
    write_file("/etc/bind/named.conf.options", named_conf_options)

    # Create a zone file for your domain
    db_ooyoosev_com = """$TTL    604800
    @       IN      SOA     ns1.ooyoosev.com. admin.ooyoosev.com. (
                      3     ; Serial
                 604800     ; Refresh
                  86400     ; Retry
                2419200     ; Expire
                 604800 )   ; Negative Cache TTL
    ;
    @       IN      NS      ns1.ooyoosev.com.
    @       IN      A       919.191.9.9
    ns1     IN      A       919.191.9.9
    www     IN      A       919.191.9.9"""
    write_file("/etc/bind/db.ooyoosev.com", db_ooyoosev_com)

    # Add the zone to named.conf.local
    named_conf_local = """zone "ooyoosev.com" {
        type master;
        file "/etc/bind/db.ooyoosev.com";
    };"""
    with open("/etc/bind/named.conf.local", 'a') as f:
        f.write(named_conf_local)

    # Restart BIND
    run_command("sudo systemctl restart bind9")

    # Enable BIND to start on boot
    run_command("sudo systemctl enable bind9")

    print("DNS server setup completed successfully.")

def create_app():
    app = Flask(__name__)

    @app.route('/')
    def home():
        return jsonify({"message": "Welcome to the super fast work server!"})

    @app.route('/api/data', methods=['POST'])
    def handle_data():
        return jsonify({"message": "Data received", "data": request.json})

    @app.errorhandler(500)
    def server_error(error):
        return jsonify({"message": "Something went wrong!"}), 500

    return app

def worker_process():
    app = create_app()
    port = int(os.environ.get('PORT', 3000))
    print(f"Worker {os.getpid()} started, listening on port {port}")
    app.run(port=port, use_reloader=False)

def health_check():
    while True:
        time.sleep(30)
        print(f"Worker {os.getpid()} is healthy")

if __name__ == '__main__':
    # Setup DNS server
    setup_dns_server()

    # Start the fast work server
    num_cpus = multiprocessing.cpu_count()
    print(f"Master {os.getpid()} is running")

    workers = []
    for _ in range(num_cpus):
        p = multiprocessing.Process(target=worker_process)
        p.start()
        workers.append(p)

    health_check_process = multiprocessing.Process(target=health_check)
    health_check_process.start()

    for worker in workers:
        worker.join()

    health_check_process.terminate()
