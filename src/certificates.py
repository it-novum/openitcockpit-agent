import datetime
import errno
import hashlib
import json
import os
import traceback
from threading import Lock

import OpenSSL
import requests
import urllib3
from OpenSSL.SSL import FILETYPE_PEM
from OpenSSL.crypto import (dump_certificate_request, dump_privatekey, load_certificate, PKey, TYPE_RSA, X509Req)

from agent_log import AgentLog
from config import Config
from exceptions import UntrustedAgentException
from filesystem import Filesystem


class Certificates:
    RENEWAL_SUCESSFUL = 1
    UNTRUSTED_AGENT = 2
    RENEWAL_ERROR = 3

    def __init__(self, config, agent_log):
        self.Config: Config = config
        self.agent_log: AgentLog = agent_log

        self.days_until_cert_warning = 120
        self.days_until_ca_warning = 30

        self.cert_checksum = None
        self.certificate_check_lock = Lock()
        self.checksum_lock = Lock()

    def get_csr(self) -> FILETYPE_PEM:
        """Function that creates a new Certificate signing request (CSR)

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
            req.get_subject().CN = self.Config.config.get('oitc', 'hostuuid') + '.agent.oitc'

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

            # b'sha512' will throw an error so we pass a string even if the function docs says it wants a byte string
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
            self.agent_log.stacktrace(traceback.format_exc())

            return False

    def requires_new_certificate(self) -> bool:
        """Checks if new autossl certificates are required if:
         - no agent certificate exists
        """

        if not self.Config.autossl:
            return False

        # Check if agent certificate file exists
        if not Filesystem.file_readable(self.Config.config['default']['autossl-crt-file']):
            self.agent_log.warning(
                'Could not read agent certificate file %s' % self.Config.config['default']['autossl-crt-file']
            )
            return True

        # Check if CA certificate file exists
        if not Filesystem.file_readable(self.Config.config['default']['autossl-ca-file']):
            self.agent_log.warning(
                'Could not read CA certificate file %s' % self.Config.config['default']['autossl-ca-file']
            )
            return True

        return False

    def requires_certificate_renewal(self) -> bool:
        """Checks if a autossl certificates requires a renewal:
         - agent certificate expire soon
         - CA certificate expires soon
        """

        # Check if agent certificate will expire soon
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
                                  int(exp_day)) - datetime.datetime.now().date()).split(',')[0], exp_date
            ))

            if datetime.date(int(exp_year), int(exp_month),
                             int(exp_day)) - datetime.datetime.now().date() <= datetime.timedelta(
                self.days_until_cert_warning):
                self.agent_log.warning(
                    'Agent SSL certificate will expire soon. Try to create a new one automatically ...')
                return True

        # Check if CA certificate will expire soon
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
                    return True

        return False

    def check_auto_certificate(self) -> bool:
        """Function to check the automatically generated certificate

        This function checks if the automatically generated certificate is installed and will otherwise trigger the download.
        In addition it checks if the certificate will expire soon.

        """

        self.agent_log.info('Checking auto TLS certificate')

        trigger_reload = False
        if self.requires_new_certificate():
            result = self._pull_crt_from_server(renew=False)
            if result == self.RENEWAL_SUCESSFUL:
                trigger_reload = True

            if result == self.UNTRUSTED_AGENT:
                # throw the UntrustedAgentException to the function the calls check_auto_certificate
                # so it can set the certificate check interval to 60 seconds instead of 6 hours
                raise UntrustedAgentException

        if Filesystem.file_readable(self.Config.config['default']['autossl-crt-file']):
            if self.requires_certificate_renewal():
                result = self._pull_crt_from_server(renew=True)
                if result == self.RENEWAL_SUCESSFUL:
                    trigger_reload = True

                if result == self.UNTRUSTED_AGENT:
                    # throw the UntrustedAgentException to the function the calls check_auto_certificate
                    # so it can set the certificate check interval to 60 seconds instead of 6 hours
                    raise UntrustedAgentException

        return trigger_reload

    def _pull_crt_from_server(self, renew=False) -> int:
        """Function to pull a new certificate using a Certificate signing request (CSR)

        This function tries to pull a new certificate from the configured openITCOCKPIT Server.
        Therefore a new certificate signing request (CSR) is needed and self.get_csr() will be called.
        The request with the CSR should return the new client and CA certificate.

        If the agent is not yet trusted by the openITCOCKPIT Server a manual confirmation in the openITCOCKPIT frontend is needed!

        If an existing certificate expired, a sha512 checksum has to be sent with the request to the openITCOCKPIT Server.
        With that checksum the server can validate, that the request was sent from a trusted agent (that has access to the old certificate).

        Returns
        -------
        int
        1 = successful => self.RENEWAL_SUCESSFUL
        2 = untrusted agent => self.UNTRUSTED_AGENT
        3 = other error => self.RENEWAL_ERROR
        """

        # ONLY PULL cert if Agent is running in PUSH mode!!
        if not self.Config.is_push_mode:
            return self.RENEWAL_ERROR

        if self.certificate_check_lock.locked():
            self.agent_log.error('Function to pull a new certificate is locked by another thread!')
            return self.RENEWAL_ERROR

        # with self.certificate_check_lock is a shortcut for:
        # self.certificate_check_lock.acquire()
        # do_something()
        # self.certificate_check_lock.release()
        with self.certificate_check_lock:
            self.agent_log.info('Pulling Certificate Signing Request (CSR) file from Server')

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
                    data['checksum'] = self.get_cert_checksum()

                try:
                    urllib3.disable_warnings()
                except:
                    self.agent_log.stacktrace(traceback.format_exc())

                response = requests.post(
                    self.Config.config['oitc']['url'].strip() + '/agentconnector/certificate.json',
                    data=data,
                    headers=headers,
                    verify=False
                )

                if response.content.decode('utf-8').strip() != '':
                    jdata = json.loads(response.content.decode('utf-8'))

                    if 'checksum_missing' in jdata:
                        self.agent_log.error('Agent certificate already generated. May be hijacked?')
                        self.agent_log.info(
                            'Add old certificate checksum to request or recreate Agent in openITCOCKPIT.'
                        )
                        return self.RENEWAL_ERROR

                    if 'unknown' in jdata:
                        # self.agent_log.error(
                        #    'Agent state is untrusted! Try again in 1 minute to get a certificate from the server.'
                        # )

                        return self.UNTRUSTED_AGENT

                    if 'signed' in jdata and 'ca' in jdata:
                        self.store_cert_file(jdata['signed'])
                        self.store_ca_file(jdata['ca'])

                        self.agent_log.info('Certificate updated successfully')

                        # Successfully get PULLED a new certificate
                        return self.RENEWAL_SUCESSFUL

            except:
                self.agent_log.error('An error occurred during autossl certificate renewal process')
                self.agent_log.stacktrace(traceback.format_exc())

            else:
                self.agent_log.error(
                    'Agent is not running in PUSH mode or no openITCOCKPIT API Configuration found in config.cnf - Certificate Signing Request not possible'
                )

        # error
        return self.RENEWAL_ERROR

    def get_cert_checksum(self) -> str:
        """Returns the current sha512 checksum of the agent certificate"""

        self.checksum_lock.acquire()
        if self.cert_checksum is None:
            with open(self.Config.config['default']['autossl-crt-file'], 'rb') as f:
                cert = f.read()
                # cert = cert.replace("\r\n", "\n")

                sha512 = hashlib.sha512()
                sha512.update(cert)
                self.cert_checksum = sha512.hexdigest().upper()

        cert_checksum = self.cert_checksum
        self.checksum_lock.release()

        # self.agent_log.debug(cert_checksum)
        return cert_checksum

    def store_cert_file(self, cert_data: str) -> bool:
        self.checksum_lock.acquire()
        self.agent_log.info('Update certificate files')
        try:
            self.cert_checksum = None

            with open(self.Config.config['default']['autossl-crt-file'], 'wb+') as f:
                f.write(cert_data.encode())

                self.checksum_lock.release()
                return True

        except:
            self.agent_log.error("An error occurred while saving new agent certificate")
            self.agent_log.stacktrace(traceback.format_exc())

            self.checksum_lock.release()
            return False

    def store_ca_file(self, ca_data: str) -> bool:
        self.checksum_lock.acquire()
        self.agent_log.info('Update CA certificate files')
        try:
            self.cert_checksum = None

            with open(self.Config.config['default']['autossl-ca-file'], 'wb+') as f:
                f.write(ca_data.encode())

                self.checksum_lock.release()
                return True

        except:
            self.agent_log.error("An error occurred while saving new CA certificate")
            self.agent_log.stacktrace(traceback.format_exc())

            self.checksum_lock.release()
            return False
