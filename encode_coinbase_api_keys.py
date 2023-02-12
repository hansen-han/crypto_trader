import io

#initialize strings
strApiKey = "APIKEY"
strApiSecret = "APISECRET"
strPassKey = "APIPASSKEY"

#save the api key as a binary file
f = open('cb_file1.bin', "wb")
strBytes = strApiKey.encode()
f.write(strBytes)
f.close()

#save the api key as a binary file
f = open('cb_file2.bin', "wb")
strBytes = strApiSecret.encode()
f.write(strBytes)
f.close()

#save the api key as a binary file
f = open('cb_file3.bin', "wb")
strBytes = strPassKey.encode()
f.write(strBytes)
f.close()