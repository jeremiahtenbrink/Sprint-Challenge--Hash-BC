#  Hint:  You may not need all of these.  Remove the unused functions.
from hashtables import (HashTable,
                        hash_table_insert,
                        hash_table_remove,
                        hash_table_retrieve,
                        hash_table_resize)


class Ticket:
    def __init__(self, source, destination):
        self.source = source
        self.destination = destination


def reconstruct_trip(tickets, length):
    hashtable = HashTable(length)
    route = [None] * (length - 1)
    for i in range(length):
        ticket = tickets[i]
        source = ticket.source
        destination = ticket.destination
        hash_table_insert(hashtable, source,
                          destination)

    flight = hash_table_retrieve(hashtable, "NONE")
    i = 0
    while flight != "NONE":
        route[i] = flight
        flight = hash_table_retrieve(hashtable, flight)
        i += 1

    return route
