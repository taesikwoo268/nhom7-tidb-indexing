FROM mysql:8.4.11
COPY --chmod=0444 mysql.cnf /etc/mysql/conf.d/custom.cnf
