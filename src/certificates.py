import datetime
import errno
import json
import os
import traceback
from threading import Lock

import OpenSSL
import ssl
import hashlib
import urllib3
import requests

from src.config import Config
from src.agent_log import AgentLog
from src.filesystem import Filesystem

from OpenSSL.SSL import FILETYPE_PEM
from OpenSSL.crypto import (dump_certificate_request, dump_privatekey, load_certificate, PKey, TYPE_RSA, X509Req)


class Certificates:

    def __init__(self, config, agent_log):
        self.Config: Config = config
        self.agent_log: AgentLog = agent_log

        self.sha512 = hashlib.sha512()

        self.days_until_cert_warning = 120
        self.days_until_ca_warning = 30

        self.cert_checksum = None
        self.certificate_check_lock = Lock()

    def get_csr(self) -> FILETYPE_PEM:
        """Function that creates a new certificate request (csr)

        Creates a RSA (4096) certificate request.
        The hostname is config['oitc']['hostuuid'] + '.agent.oitc'.

        Writes csr in the default or custom autossl-csr-file.

        Writes certificate key in the default or custom autossl-key-file.


        Returns
        -------
        FILETYPE_PEM
            Returns a pem object (FILETYPE_PEM) on success

        """

        try:

            # ECC (not working yet)
            #
            # from Crypto.PublicKey import ECC
            #
            # key = ECC.generate(curve='prime256v1')
            # req = X509Req()
            # req.get_subject().CN = config['oitc']['hostuuid']+'.agent.oitc'
            # publicKey = key.public_key().export_key(format='PEM', compress=False)
            # privateKey = key.export_key(format='PEM', compress=False, use_pkcs8=True)
            #
            # pubdict = {}
            # pubdict['_only_public'] = publicKey
            # req.sign(publicKey, 'sha384')

            self.agent_log.info('Creating new Certificate Signing Request (CSR)')

            # create public/private key
            key = PKey()
            key.generate_key(TYPE_RSA, 4096)

            # Generate CSR
            req = X509Req()
            req.get_subject().CN = self.Config.config.get('oitc' 'hostuuid') + '.agent.oitc'

            # Experimental; not supported by php agent csr sign method yet
            san_list = ["DNS:localhost", "DNS:127.0.0.1"]
            req.add_extensions([
                OpenSSL.crypto.X509Extension(b"subjectAltName", True, (", ".join(san_list)).encode('ascii'))
            ])

            # req.get_subject().O = 'XYZ Widgets Inc'
            # req.get_subject().OU = 'IT Department'
            # req.get_subject().L = 'Seattle'
            # req.get_subject().ST = 'Washington'
            # req.get_subject().C = 'US'
            # req.get_subject().emailAddress = 'e@example.com'
            req.set_pubkey(key)
            req.sign(key, b'sha512')

            ssl_paths = [
                self.Config.config['default']['autossl-csr-file'],
                self.Config.config['default']['autossl-key-file'],
                self.Config.config['default']['autossl-crt-file'],
                self.Config.config['default']['autossl-ca-file']
            ]

            for filename in ssl_paths:
                if not os.path.exists(os.path.dirname(filename)):
                    try:
                        os.makedirs(os.path.dirname(filename))
                    except OSError as exc:  # Guard against race condition
                        if exc.errno != errno.EEXIST:
                            self.agent_log.error('An error occurred while creating the ssl files containing folders')
                            if self.Config.stacktrace:
                                raise

            csr = dump_certificate_request(FILETYPE_PEM, req)
            with open(self.Config.config['default']['autossl-csr-file'], 'wb+') as f:
                f.write(csr)
            with open(self.Config.config['default']['autossl-key-file'], 'wb+') as f:
                f.write(dump_privatekey(FILETYPE_PEM, key))

            self.agent_log.info('CSR file written')

            return csr
        except:
            self.agent_log.error('An error occurred while creating a new Certificate Signing Request (CSR)')

            if self.Config.stacktrace:
                traceback.print_exc()

            return False

    def check_auto_certificate(self):
        """Function to check the automatically generated certificate

        This function checks if the automatically generated certificate is installed and will otherwise trigger the download.
        In addition it checks if the certificate will expire soon.

        """
        self.agent_log.info('Checking auto TLS certificate')
        request_new_certificate = False
        if not Filesystem.file_readable(self.Config.config['default']['autossl-crt-file']):
            self.agent_log.warning(
                'Could not read certificate file %s' % self.Config.config['default']['autossl-crt-file'])
            self.pull_crt_from_server()
        if Filesystem.file_readable(
                self.Config.config['default'][
                    'autossl-crt-file']):  # repeat condition because pull_crt_from_server could fail
            self.agent_log.warning(
                'Could not read certificate file %s' % self.Config.config['default']['autossl-crt-file'])

            with open(self.Config.config['default']['autossl-crt-file'], 'rb') as f:
                cert = f.read()
                x509 = load_certificate(FILETYPE_PEM, cert)
                x509info = x509.get_notAfter()
                exp_day = x509info[6:8].decode('utf-8')
                exp_month = x509info[4:6].decode('utf-8')
                exp_year = x509info[:4].decode('utf-8')
                exp_date = str(exp_day) + "-" + str(exp_month) + "-" + str(exp_year)

                self.agent_log.info("SSL Certificate expires in %s on %s (DD-MM-YYYY)" % (
                    str(datetime.date(int(exp_year),
                                      int(exp_month),
                                      int(exp_day)) - datetime.datetime.now().date()).split(',')[
                        0], exp_date))

                if datetime.date(int(exp_year), int(exp_month),
                                 int(exp_day)) - datetime.datetime.now().date() <= datetime.timedelta(
                    self.days_until_cert_warning):
                    self.agent_log.warning(
                        'SSL Certificate will expire soon. Try to create a new one automatically ...')
                    request_new_certificate = True

        if Filesystem.file_readable(self.Config.config['default']['autossl-ca-file']):
            self.agent_log.info('CA file %s found and readable' % self.Config.config['default']['autossl-ca-file'])
            with open(self.Config.config['default']['autossl-ca-file'], 'rb') as f:
                ca = f.read()
                x509 = load_certificate(FILETYPE_PEM, ca)
                x509info = x509.get_notAfter()
                exp_day = x509info[6:8].decode('utf-8')
                exp_month = x509info[4:6].decode('utf-8')
                exp_year = x509info[:4].decode('utf-8')
                exp_date = str(exp_day) + "-" + str(exp_month) + "-" + str(exp_year)

                if datetime.date(int(exp_year), int(exp_month),
                                 int(exp_day)) - datetime.datetime.now().date() <= datetime.timedelta(
                    self.days_until_ca_warning):
                    self.agent_log.warning("CA Certificate expires in %s on %s (DD-MM-YYYY)" % (
                        str(datetime.date(int(exp_year), int(exp_month),
                                          int(exp_day)) - datetime.datetime.now().date()).split(
                            ',')[0], exp_date))
                    request_new_certificate = True

        if request_new_certificate:
            self.agent_log.info('Try pulling new Certificate from monitoring server')
            if self.pull_crt_from_server(True) is not False:
                self.check_auto_certificate()

    def pull_crt_from_server(self, renew=False):
        """Function to pull a new certificate using a csr

        This function tries to pull a new certificate from the configured openITCOCKPIT Server.
        Therefore a new certificate request (csr) is needed and get_csr() will be called.
        The request with the csr should return the new client (and the CA) certificate.

        If the agent is not known and not yet trusted by the openITCOCKPIT Server the function will be executed again in 10 minutes.
        Therefore the function wait_and_check_auto_certificate(600) will be called as new thread (future).

        If the agent is not yet trusted by the openITCOCKPIT Server a manual confirmation in the openITCOCKPIT frontend is needed!

        If an existing certificate expired, a sha512 checksum has to be sent with the request to the openITCOCKPIT Server.
        With that checksum the server can validate, that the request was sent from a trusted agent (that has access to the old certificate).

        Returns
        -------
        bool
            True if successful, False otherwise.

        """

        self.agent_log.info('Pulling Certificate Signing Request (CSR) file from Server')

        if self.certificate_check_lock.locked():
            self.agent_log.error('Function to pull a new certificate is locked by another thread!')
            return False

        with self.certificate_check_lock:
            if self.Config.config['oitc']['url'] and self.Config.config['oitc']['url'] != "" and \
                    self.Config.config['oitc']['apikey'] and self.Config.config['oitc']['apikey'] != "" and \
                    self.Config.config['oitc']['hostuuid'] and self.Config.config['oitc']['hostuuid'] != "":
                try:
                    csr = self.get_csr()

                    data = {
                        'csr': csr.decode(),
                        'hostuuid': self.Config.config['oitc']['hostuuid']
                    }
                    headers = {
                        'Content-Type': 'application/x-www-form-urlencoded',
                        'Authorization': 'X-OITC-API ' + self.Config.config['oitc']['apikey'].strip(),
                    }
                    if renew:
                        with open(self.Config.config['default']['autossl-crt-file'], 'rb') as f:
                            cert = f.read()
                            #cert = cert.replace("\r\n", "\n")
                            self.sha512.update(cert)
                            data['checksum'] = self.sha512.hexdigest().upper()

                    try:
                        urllib3.disable_warnings()
                    except:

                        if self.Config.stacktrace:
                            traceback.print_exc()

                    response = requests.post(
                        self.Config.config['oitc']['url'].strip() + '/agentconnector/certificate.json',
                        data=data,
                        headers=headers,
                        verify=False)
                    if response.content.decode('utf-8').strip() != '':
                        jdata = json.loads(response.content.decode('utf-8'))

                        if 'checksum_missing' in jdata:
                            self.agent_log.error('Agent certificate already generated. May be hijacked?')
                            self.agent_log.info(
                                'Add old certificate checksum to request or recreate Agent in openITCOCKPIT.')

                        if 'unknown' in jdata:
                            self.agent_log.error(
                                'Agent state is untrusted! Try again in 1 minute to get a certificate from the server.')

                            #print_verbose(
                            #    'Untrusted agent! Try again in 1 minute to get a certificate from the server.',
                            #    False)
                            #agent_log.warning(
                            #    'Untrusted agent! Try again in 1 minute to get a certificate from the server.')
                            #executor = futures.ThreadPoolExecutor(max_workers=1)
                            #executor.submit(wait_and_check_auto_certificate, 60)

                        if 'signed' in jdata and 'ca' in jdata:
                            with open(self.Config.config['default']['autossl-crt-file'], 'wb+') as f:
                                f.write(jdata['signed'])
                                self.sha512.update(jdata['signed'].encode())
                                self.cert_checksum = self.sha512.hexdigest().upper()
                            with open(self.Config.config['default']['autossl-ca-file'], 'wb+') as f:
                                f.write(jdata['ca'])

                            restart_webserver()

                            self.agent_log.info('Signed certificate updated successfully')
                            return True
                except:
                    self.agent_log.error('An error occurred during autossl certificate renewal process')

                    if self.Config.stacktrace:
                        traceback.print_exc()

        return False
