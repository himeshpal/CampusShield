# Department website on Apache 2.4.49 - the version affected by CVE-2021-41773.
# The stock config is kept (root directory "Require all denied"), so the path traversal
# is not actually exploitable here; CampusShield detects the risk from the version banner.
FROM httpd:2.4.49
COPY index.html /usr/local/apache2/htdocs/index.html
