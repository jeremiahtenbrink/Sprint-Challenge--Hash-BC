import hashlib
import requests
import multiprocessing
import sys
import time

from timeit import default_timer as timer

import random

NUMBER_OF_THREADS = 6
BLOCK_CHECK_TIME = 9
NODE = "https://lambda-coin-test-1.herokuapp.com/api"
ID = "UNKNOWN"


def start_loop():
    global NUMBER_OF_THREADS
    number_of_mined_coins = 0
    mining_block = None
    thread_storage = [None] * NUMBER_OF_THREADS
    threads_manager = multiprocessing.Manager()
    valid_guesses = []
    mining_results = None
    head_start_active = False
    mining_try = 1
    # Run forever until interrupted
    while True:

        new_block = get_block()
        if mining_block is None or new_block != mining_block:
            mining_try = 1
            print("Mining timers count reset to 1.")
            mining_block = new_block
            valid_guesses = start_new_block(head_start_active, thread_storage,
                                            mining_block, threads_manager)

        else:
            if head_start_active:
                print("Head start worked.")
            else:
                print("No new block, continuing to mine current block.")

        head_start_active = False

        mining_result = check_threads(thread_storage, valid_guesses,
                                      mining_try)

        if mining_result == "reset":
            mining_try += 1
            print(f"Number of timers on current block is {mining_try}.")
            print('Checking for new block')
            continue
        else:
            mining_block = mining_result
            print(f"Valid guess is {mining_result}")
            submit_data = threads_manager.dict()

            submit_thread = multiprocessing.Process(
                target = submit_results, args = (number_of_mined_coins,
                                                 mining_result,
                                                 submit_data))
            submit_thread.start()

            head_start_active = True
            [number_of_mined_coins, valid_guesses] = engage_head_start(
                thread_storage,
                mining_block,
                threads_manager,
                submit_thread, submit_data)

            mining_try = 1
            print("Mining timers count reset to 1.")


def start_new_block(head_start, threads, block, process_manager):
    if head_start:
        print("Failed head start. Stopping head start threads")
        stop_threads(threads)

    print("Retrieved new block.")
    valid_guesses = start_threads(block, threads,
                                  process_manager)
    return valid_guesses


def engage_head_start(threads, block, threads_manager, sub_thread, sub_data):
    print('Head start engaged.')
    stop_threads(threads)
    valid_guesses = start_threads(block, threads,
                                  threads_manager)
    sub_thread.join()
    results = sub_data.values()
    return [results[0], valid_guesses]


def get_block():
    got_response = False
    new_block = None
    while not got_response:
        req_res = requests.get(url = NODE + "/last_proof")
        try:
            data_from_request = req_res.json()
            new_block = data_from_request['proof']
            got_response = True
        except ValueError:
            print("Error:  Non-json response")
            print("Response returned:")
            print(req_res)
            continue

    return new_block


def stop_threads(thread_array):
    print('Stopping all threads.')

    # loop through each thread in the threads array
    for i in range(len(thread_array)):
        proc = thread_array[i]
        if proc is not None:
            if proc.is_alive():
                proc.terminate()
            print(f"Stopped thread {i}")


def start_threads(current_block, threads_array, data_manager):
    manger_dict = data_manager.dict()
    print(f'Starting {NUMBER_OF_THREADS} new threads.')
    block_encoded = f"{current_block}".encode()
    prev_hash = hashlib.sha256(block_encoded).hexdigest()
    last_six = prev_hash[-6:]
    seed_number = random.randint(0, 500000)
    for i in range(NUMBER_OF_THREADS):
        thread = multiprocessing.Process(target = proof_of_work,
                                         args = (last_six, i, manger_dict,
                                                 seed_number))
        threads_array[i] = thread
        thread.start()
    return manger_dict


def proof_of_work(last_hash_last_6, i, place_to_put_valid_guesses,
                  random_number):
    """
    Multi-Ouroboros of Work Algorithm
    - Find a number p' such that the last six digits of hash(p) are equal
    to the first six digits of hash(p')
    - IE:  last_hash: ...AE9123456, new hash 123456888...
    - p is the previous proof, and p' is the new proof
    - Use the same method to generate SHA-256 hashes as the examples in class
    """
    start = timer()
    print(f'Starting thread {i}')
    proof = i * 1000000000 + random_number
    not_valid = True
    while not_valid:
        if valid_proof(last_hash_last_6, proof):
            not_valid = False
        else:
            proof += 1
    print("Proof found: " + str(proof) + " in " + str(
        timer() - start) + f" on thread {i}")
    place_to_put_valid_guesses[i] = proof


def valid_proof(hash_last_six, proof):
    """
    Validates the Proof:  Multi-ouroborus:  Do the last six characters of
    the hash of the last proof match the first six characters of the hash
    of the new proof?

    IE:  last_hash: ...AE9123456, new hash 123456E88...
    """
    proof = f"{proof}".encode()

    proof_hash = hashlib.sha256(proof).hexdigest()

    first_6 = proof_hash[:6]
    if first_6 == hash_last_six:
        return True
    else:
        return False


def check_threads(thread_array, threads_dict, try_number):
    global BLOCK_CHECK_TIME
    seconds = BLOCK_CHECK_TIME / try_number
    if seconds < 1:
        seconds = 1
    print(f"Starting mining timer for {seconds} seconds.")
    thread_timer = multiprocessing.Process(target = time_process,
                                           args = (seconds,))
    thread_timer.start()

    while True:
        # check threads
        time.sleep(.01)
        valid_guess = check_for_valid_answer(threads_dict)
        if valid_guess:
            print("Valid guess collected.")
            print('Stopping mining timer')
            if thread_timer.is_alive():
                thread_timer.terminate()
            return valid_guess

        # check if timer is still running.
        timer_alive = thread_timer.is_alive()
        if not timer_alive:

            # check for valid answer one last time
            valid_guess = check_for_valid_answer(threads_dict)
            if valid_guess:
                return valid_guess

            print('Returning rest from check threads.')
            return "reset"


def check_for_valid_answer(threads_data):
    data = threads_data.values()
    if len(data) > 0:
        return data[0]
    return False


def submit_results(number_of_coins, proof, return_array):
    global ID
    global NODE
    print("Submitting proof")
    post_data = {"proof": proof,
                 "id": ID}

    posted = False
    post_try_count = 0
    submitted = False
    while post_try_count <= 3 and not submitted:
        r = requests.post(url = NODE + "/mine", json = post_data)
        if post_try_count < 3:
            try:
                data = r.json()
                submitted = True
            except ValueError:
                print("Error:  Non-json response")
                print("Response returned:")
                print(r)
                post_try_count += 1
                continue

            if data.get('message') == 'New Block Forged':
                number_of_coins += 1
                print("Valid submission.")
                print("Total coins mined: " + str(number_of_coins))
            else:
                print(data.get('message'))

    return_array[0] = number_of_coins


def time_process(time_limit):
    time.sleep(time_limit)
    print('Mining timer finished.')


if __name__ == '__main__':
    # What node are we interacting with?
    seed = time.gmtime()
    random.seed(seed.tm_sec)
    if len(sys.argv) > 1:
        NODE = sys.argv[1]

    # Load or create ID
    f = open("my_id.txt", "r")
    id = f.read()
    print("ID is", id)
    f.close()

    if id == 'NONAME\n':
        print("ERROR: You must change your name in `my_id.txt`!")
        exit()

    start_loop()
