import hashlib
import requests
import multiprocessing
import sys
import time
import random

from uuid import uuid4

from timeit import default_timer as timer

import random

threads = []
process_timer = "None"
block = None
valid_guesses = None
manager = None


def proof_of_work(last_proof, i, valid_guesses):
    """
    Multi-Ouroboros of Work Algorithm
    - Find a number p' such that the last six digits of hash(p) are equal
    to the first six digits of hash(p')
    - IE:  last_hash: ...AE9123456, new hash 123456888...
    - p is the previous proof, and p' is the new proof
    - Use the same method to generate SHA-256 hashes as the examples in class
    """

    start = timer()
    last_hash = f"{last_proof}".encode()
    last_hash = hashlib.sha256(last_hash).hexdigest()

    proof = i * 1000000000 + random.randint(0, 500000)
    not_valid = True
    while not_valid:
        if valid_proof(last_hash, proof):
            not_valid = False
        else:
            proof += 1
    valid_guesses[i] = proof

    print("Proof found: " + str(proof) + " in " + str(
        timer() - start) + f" on thread {i}")


def valid_proof(last_hash, proof):
    """
    Validates the Proof:  Multi-ouroborus:  Do the last six characters of
    the hash of the last proof match the first six characters of the hash
    of the new proof?

    IE:  last_hash: ...AE9123456, new hash 123456E88...
    """
    proof = f"{proof}".encode()

    proof_hash = hashlib.sha256(proof).hexdigest()
    last_6 = last_hash[-6:]
    first_6 = proof_hash[:6]
    if first_6 == last_6:

        return last_6 == first_6
    else:
        return False


def time_process():
    time.sleep(8)


def get_request():
    got_response = False
    while not got_response:
        r = requests.get(url = node + "/last_proof")
        try:
            data = r.json()
            block = data['proof']
            got_response = True
        except ValueError:
            print("Error:  Non-json response")
            print("Response returned:")
            print(r)
            continue

    return block


def start_loop():
    # Run forever until interrupted
    global threads
    global process_timer
    global block
    global valid_guesses
    global manager
    if manager == None:
        manager = multiprocessing.Manager()
    # Get the last proof from the server
    new_block = get_request()
    changed_block = False
    if block != new_block:
        print('New block found!');
        changed_block = True
        block = new_block
    else:
        print('No new block found. Continuing to mine.')

    if process_timer is not "None" and process_timer.is_alive():
        process_timer.terminate()

    if changed_block:
        print("Stopping all prev threads")
        valid_guesses = manager.dict()
        for proc in threads:
            if proc.is_alive:
                proc.terminate()
        print('Starting new threads.')
        for i in range(6):
            thread = multiprocessing.Process(target = proof_of_work,
                                             args = (block, i,
                                                     valid_guesses))
            threads.append(thread)
            thread.start()

    process_timer = multiprocessing.Process(target = time_process())

    valid_guess = False
    reset = False
    while not valid_guess and not reset:
        for proc in threads:
            if valid_guess:
                break
            if not proc.is_alive():
                valid_guess = True
                if process_timer.is_alive():
                    process_timer.terminate()

        if not process_timer.is_alive() and not valid_guess:
            for proc in threads:
                if valid_guess:
                    break
                if not proc.is_alive():
                    valid_guess = True
                    if process_timer.is_alive():
                        process_timer.terminate()
                        break

            if valid_guess:
                if process_timer.is_alive():
                    process_timer.terminate()
            else:
                reset = True
                break

    if (reset and not valid_guess) or len(valid_guesses.values()) == 0:
        print('timed out. Checking for new block')
        return "reset"

    valid_guess = valid_guesses.values()
    proof = valid_guess[0]
    return proof


if __name__ == '__main__':
    # What node are we interacting with?
    seed = time.gmtime()
    random.seed(seed.tm_sec)
    if len(sys.argv) > 1:
        node = sys.argv[1]
    else:
        node = "https://lambda-coin-test-1.herokuapp.com/api"

    coins_mined = 0

    # Load or create ID
    f = open("my_id.txt", "r")
    id = f.read()
    print("ID is", id)
    f.close()

    if id == 'NONAME\n':
        print("ERROR: You must change your name in `my_id.txt`!")
        exit()

    while True:
        response = start_loop()
        if response == "reset":
            continue
        else:
            print("submitting proof")
            post_data = {"proof": response,
                         "id": id}

            r = requests.post(url = node + "/mine", json = post_data)
            try:
                data = r.json()
            except ValueError:
                print("Error:  Non-json response")
                print("Response returned:")
                print(r)
                continue
            if data.get('message') == 'New Block Forged':
                coins_mined += 1
                print("Total coins mined: " + str(coins_mined))
            else:
                print(data.get('message'))
