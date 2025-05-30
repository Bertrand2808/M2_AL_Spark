#!/usr/bin/env python3

import random
import sys
import time



def randomip():
    return ".".join(str(random.randint(0, 255)) for _ in range(4))



def randomstring(n):
    charset = "abcdefghikjlmnopqrstuvwxyzABCDEFGHIKJLMNOPQRSTUVWXYZ0123456789"
    return "".join(random.choice(charset) for _ in range(n))



def randomurl():
    return "https://localhost/" + randomstring(random.randint(4, 16))



def main():
    if len(sys.argv) != 3:
        print("usage: %s numusers numurls" % sys.argv[0])
        return

    nusers = int(sys.argv[1])
    nurls = int(sys.argv[2])

    users = [randomip() for _ in range(nusers)]
    urls = [randomurl() for _ in range(nurls)]

    usersw = [2**i/(2**(i+1)-1) for i in range(nusers)]
    urlsw = [2**i/(2**(i+1)-1) for i in range(nurls)]

    while True:
        user = random.choices(users, usersw)[0]
        url = random.choices(urls, urlsw)[0]
        print("%s\t%s" % (user, url), flush=True)
        time.sleep(random.random() * 2)


if __name__ == '__main__':
    main()
