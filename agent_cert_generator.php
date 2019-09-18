<?php

class registerAgent {

    public $ECC_CA = false;
    public $days_CA = 36500;

    public $oitcID = 'ghueiXerg9858zu39Mhgi873hu';
    public $caCertPath = '/var/www/html/testcrts/test_ecc_ca2.pem';
    public $caKeyPath = '/var/www/html/testcrts/test_ecc_ca2.key';
    
    public function __construct() {
        if(!is_file($this->caCertPath)){
            // Generate initial agent server ca certificate
            $subject = array(
                "commonName" => $this->oitcID.'.agentserver.oitc',
            );

            // Generate a new private key
            $digest_alg = 'sha512';
            $private_key = openssl_pkey_new(array(
                "private_key_type" => OPENSSL_KEYTYPE_RSA,
                "digest_alg" => $digest_alg,
                "private_key_bits" => 4096,
            ));
            if($this->ECC_CA){
                $digest_alg = 'sha384';
                $private_key = openssl_pkey_new(array(
                    "private_key_type" => OPENSSL_KEYTYPE_EC,
                    "curve_name" => 'prime256v1',
                ));
            }

            $csr = openssl_csr_new($subject, $private_key, array('digest_alg' => $digest_alg));

            $x509 = openssl_csr_sign($csr, null, $private_key, $days=$this->days_CA, array('digest_alg' => $digest_alg), time());
            openssl_x509_export_to_file($x509, $this->caCertPath);
            openssl_pkey_export_to_file($private_key, $this->caKeyPath);
            sleep(1);
        }

        if(isset($_POST['csr'])){
            echo json_encode($this->signAgentCsr($_POST['csr']));
            //should return this if agent is unknown and needs to be confirmed by an user
            #echo json_encode(['unknown' => true]);
        }
    }
    
    public function signAgentCsr($csr){
        // Generate signed cert from csr
        $x509 = openssl_csr_sign($csr, file_get_contents($this->caCertPath), file_get_contents($this->caKeyPath), $days=365, array('digest_alg' => 'sha512', 'x509_extensions' => 'v3_req'), time());
        
        openssl_x509_export($x509, $signedPublic);
        #openssl_x509_export_to_file($x509, '/var/www/html/testcrts/test_agent_csr_cert.pem');
        
        return ["signed" => $signedPublic, "ca" => file_get_contents($this->caCertPath)];
    }
}

function connectToAgent($ip, $port, $register){
    $useSSL = false;
    
    $curl_get = curl_init();
    curl_setopt_array($curl_get, [
        CURLOPT_RETURNTRANSFER => 1,
        CURLOPT_URL => 'http://'.$ip.':'.$port.'/getCsr'
    ]);
    $result = curl_exec($curl_get);
    
    if(!$result){
        curl_setopt_array($curl_get, [
            CURLOPT_RETURNTRANSFER => 1,
            CURLOPT_URL => 'https://'.$ip.':'.$port.'/getCsr',
            CURLOPT_CAINFO => $register->caCertPath,
            CURLOPT_SSLCERT => $register->caCertPath,
            CURLOPT_SSLKEY => $register->caKeyPath,
            CURLOPT_SSL_VERIFYHOST => false
        ]);
        $result = curl_exec($curl_get);
        /*
        if (curl_errno($curl_get)) {
            var_dump(curl_error($curl_get));
        }
        */

        if($result === false){
            return false;
        }
        $useSSL = True;
    }
    
    try{
        $result = json_decode($result, true);
        if(isset($result['csr']) && $result['csr'] != "disabled"){
            $data_string = json_encode($register->signAgentCsr($result['csr']));

            $curl = curl_init();
            if($useSSL){
                curl_setopt_array($curl, [
                    CURLOPT_RETURNTRANSFER => 1,
                    CURLOPT_URL => 'https://'.$ip.':'.$port.'/updateCrt',
                    CURLOPT_POST => 1,
                    CURLOPT_POSTFIELDS => $data_string,
                    CURLOPT_HTTPHEADER => [
                        'Content-Type: application/json',                                                                                
                        'Content-Length: ' . strlen($data_string)
                    ],
                    CURLOPT_CAINFO => $register->caCertPath,
                    CURLOPT_SSLCERT => $register->caCertPath,
                    CURLOPT_SSLKEY => $register->caKeyPath,
                    CURLOPT_SSL_VERIFYHOST => false
                ]);
            } else {
                curl_setopt_array($curl, [
                    CURLOPT_RETURNTRANSFER => 1,
                    CURLOPT_URL => 'http://'.$ip.':'.$port.'/updateCrt',
                    CURLOPT_POST => 1,
                    CURLOPT_POSTFIELDS => $data_string,
                    CURLOPT_HTTPHEADER => [
                        'Content-Type: application/json',                                                                                
                        'Content-Length: ' . strlen($data_string)
                    ]
                ]);
            }
            
            $resp = curl_exec($curl);
            var_dump($resp);
            
        }
    } catch (Exception $e){
        echo 'Error: ' .$e->getMessage();
    }
}


$register = new registerAgent();

//comment out to run in agent -> push to -> oitc mode
//connectToAgent('172.16.166.109', 3333, $register);




