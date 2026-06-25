# Few-Shot Example: Ansible Playbook for Nginx Deployment

**Domain:** DevOps / Configuration Management
**Skill Level:** Intermediate
**Pattern:** Idempotent, secure Ansible playbook with role structure

---

## User Query

```
Create an Ansible playbook to install and configure Nginx with SSL and security hardening.
```

---

## Exemplary Response

### Playbook Structure

```
ansible-nginx/
├── playbook.yml      # Main playbook
├── inventory.yml     # Hosts inventory
├── group_vars/
│   └── webservers.yml
└── roles/
    └── nginx/
        ├── tasks/
        │   ├── main.yml
        │   ├── install.yml
        │   ├── configure.yml
        │   └── harden.yml
        ├── templates/
        │   ├── nginx.conf.j2
        │   └── site.conf.j2
        ├── files/
        │   └── dhparam.pem
        └── handlers/
            └── main.yml
```

### Main Playbook

```yaml
# playbook.yml
---
- name: Deploy and Configure Nginx
  hosts: webservers
  become: yes
  gather_facts: yes

  pre_tasks:
    - name: Update apt cache
      apt:
        update_cache: yes
        cache_valid_time: 3600
      when: ansible_os_family == "Debian"

  roles:
    - role: nginx
      tags: ['nginx']

  post_tasks:
    - name: Verify Nginx is running
      systemd:
        name: nginx
        state: started
        enabled: yes

    - name: Test Nginx configuration
      command: nginx -t
      register: nginx_test
      changed_when: false

    - name: Display test result
      debug:
        msg: "Nginx configuration is valid"
      when: nginx_test.rc == 0
```

### Role Tasks

```yaml
# roles/nginx/tasks/main.yml
---
- name: Include installation tasks
  include_tasks: install.yml
  tags: ['install']

- name: Include configuration tasks
  include_tasks: configure.yml
  tags: ['configure']

- name: Include security hardening tasks
  include_tasks: harden.yml
  tags: ['harden']

---
# roles/nginx/tasks/install.yml
---
- name: Install Nginx
  apt:
    name: nginx
    state: present
    update_cache: yes
  when: ansible_os_family == "Debian"

- name: Install Nginx
  yum:
    name: nginx
    state: present
  when: ansible_os_family == "RedHat"

- name: Install required packages
  package:
    name:
      - certbot
      - python3-certbot-nginx
    state: present

- name: Ensure Nginx service is enabled
  systemd:
    name: nginx
    enabled: yes

---
# roles/nginx/tasks/configure.yml
---
- name: Create web root directory
  file:
    path: "{{ nginx_web_root }}"
    state: directory
    owner: www-data
    group: www-data
    mode: '0755'

- name: Deploy main Nginx configuration
  template:
    src: nginx.conf.j2
    dest: /etc/nginx/nginx.conf
    owner: root
    group: root
    mode: '0644'
    validate: 'nginx -t -c %s'
  notify: Reload Nginx

- name: Remove default site
  file:
    path: /etc/nginx/sites-enabled/default
    state: absent
  notify: Reload Nginx

- name: Deploy site configuration
  template:
    src: site.conf.j2
    dest: "/etc/nginx/sites-available/{{ nginx_site_name }}"
    owner: root
    group: root
    mode: '0644'
  notify: Reload Nginx

- name: Enable site
  file:
    src: "/etc/nginx/sites-available/{{ nginx_site_name }}"
    dest: "/etc/nginx/sites-enabled/{{ nginx_site_name }}"
    state: link
  notify: Reload Nginx

- name: Generate Let's Encrypt SSL certificate
  command: >
    certbot certonly --nginx
    -d {{ nginx_server_name }}
    --non-interactive
    --agree-tos
    --email {{ ssl_email }}
  args:
    creates: "/etc/letsencrypt/live/{{ nginx_server_name }}/fullchain.pem"
  when: nginx_ssl_enabled

---
# roles/nginx/tasks/harden.yml
---
- name: Generate strong DH parameters
  command: openssl dhparam -out /etc/nginx/dhparam.pem 2048
  args:
    creates: /etc/nginx/dhparam.pem
  when: nginx_ssl_enabled

- name: Set secure permissions on DH parameters
  file:
    path: /etc/nginx/dhparam.pem
    owner: root
    group: root
    mode: '0600'
  when: nginx_ssl_enabled

- name: Configure firewall (UFW)
  ufw:
    rule: allow
    port: "{{ item }}"
    proto: tcp
  loop:
    - '80'
    - '443'
  when: ansible_os_family == "Debian"

- name: Configure SELinux (if enabled)
  seboolean:
    name: httpd_can_network_connect
    state: yes
    persistent: yes
  when:
    - ansible_os_family == "RedHat"
    - ansible_selinux.status == "enabled"
```

### Templates

```jinja2
{# roles/nginx/templates/nginx.conf.j2 #}
user www-data;
worker_processes auto;
pid /run/nginx.pid;
error_log /var/log/nginx/error.log warn;

events {
    worker_connections 1024;
    use epoll;
}

http {
    include /etc/nginx/mime.types;
    default_type application/octet-stream;

    # Logging
    log_format main '$remote_addr - $remote_user [$time_local] "$request" '
                    '$status $body_bytes_sent "$http_referer" '
                    '"$http_user_agent" "$http_x_forwarded_for"';
    access_log /var/log/nginx/access.log main;

    # Performance
    sendfile on;
    tcp_nopush on;
    tcp_nodelay on;
    keepalive_timeout 65;
    types_hash_max_size 2048;

    # Security Headers
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;
    add_header Referrer-Policy "no-referrer-when-downgrade" always;

    # Hide Nginx version
    server_tokens off;

    # SSL Configuration
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers 'ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256';
    ssl_prefer_server_ciphers on;
    ssl_session_cache shared:SSL:10m;
    ssl_session_timeout 10m;

    # Include site configurations
    include /etc/nginx/sites-enabled/*;
}

---
{# roles/nginx/templates/site.conf.j2 #}
server {
    listen 80;
    server_name {{ nginx_server_name }};

    # Redirect HTTP to HTTPS
    {% if nginx_ssl_enabled %}
    return 301 https://$server_name$request_uri;
    {% else %}
    root {{ nginx_web_root }};
    index index.html index.htm;
    {% endif %}
}

{% if nginx_ssl_enabled %}
server {
    listen 443 ssl http2;
    server_name {{ nginx_server_name }};

    # SSL Certificates
    ssl_certificate /etc/letsencrypt/live/{{ nginx_server_name }}/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/{{ nginx_server_name }}/privkey.pem;
    ssl_dhparam /etc/nginx/dhparam.pem;

    # HSTS
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;

    root {{ nginx_web_root }};
    index index.html index.htm;

    location / {
        try_files $uri $uri/ =404;
    }

    # Security: Deny access to hidden files
    location ~ /\. {
        deny all;
    }
}
{% endif %}
```

### Handlers

```yaml
# roles/nginx/handlers/main.yml
---
- name: Reload Nginx
  systemd:
    name: nginx
    state: reloaded

- name: Restart Nginx
  systemd:
    name: nginx
    state: restarted
```

### Variables

```yaml
# group_vars/webservers.yml
---
nginx_site_name: "myapp"
nginx_server_name: "example.com"
nginx_web_root: "/var/www/{{ nginx_site_name }}"
nginx_ssl_enabled: true
ssl_email: "admin@example.com"
```

### Inventory

```yaml
# inventory.yml
---
all:
  children:
    webservers:
      hosts:
        web1:
          ansible_host: 192.168.1.10
        web2:
          ansible_host: 192.168.1.11
      vars:
        ansible_user: ubuntu
        ansible_become: yes
```

### Execution

```bash
# Syntax check
ansible-playbook playbook.yml --syntax-check

# Dry run
ansible-playbook -i inventory.yml playbook.yml --check

# Execute
ansible-playbook -i inventory.yml playbook.yml

# Execute specific tags
ansible-playbook -i inventory.yml playbook.yml --tags harden

# Verbose mode
ansible-playbook -i inventory.yml playbook.yml -vvv
```

---

## Why This Is A Good Example

✅ **Idempotent** — Safe to run multiple times
✅ **Role structure** — Modular, reusable
✅ **Security-focused** — SSL, security headers, hardening
✅ **Cross-platform** — Supports Debian and RedHat
✅ **Validation** — Tests Nginx config before reload
✅ **Handlers** — Efficient service management

---

## Key Patterns

1. **Use roles** for modularity and reusability
2. **Template validation** to prevent breaking configs
3. **Handlers** for service restarts (triggered only if needed)
4. **Tags** for selective execution
5. **become** for privilege escalation
6. **when** for conditional execution

---

**Tags:** #ansible #nginx #ssl #automation #configuration-management
**Version:** 1.0.0
**Last Updated:** 2026-01-22
