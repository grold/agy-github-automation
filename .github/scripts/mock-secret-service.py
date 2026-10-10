#!/usr/bin/env python3
import sys, os, hmac, hashlib
import dbus
import dbus.service
import dbus.mainloop.glib
from gi.repository import GLib
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.backends import default_backend

DH_PRIME_1024_BYTES = (
    0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xC9, 0x0F, 0xDA, 0xA2, 0x21, 0x68,
    0xC2, 0x34, 0xC4, 0xC6, 0x62, 0x8B, 0x80, 0xDC, 0x1C, 0xD1, 0x29, 0x02, 0x4E, 0x08,
    0x8A, 0x67, 0xCC, 0x74, 0x02, 0x0B, 0xBE, 0xA6, 0x3B, 0x13, 0x9B, 0x22, 0x51, 0x4A,
    0x08, 0x79, 0x8E, 0x34, 0x04, 0xDD, 0xEF, 0x95, 0x19, 0xB3, 0xCD, 0x3A, 0x43, 0x1B,
    0x30, 0x2B, 0x0A, 0x6D, 0xF2, 0x5F, 0x14, 0x37, 0x4F, 0xE1, 0x35, 0x6D, 0x6D, 0x51,
    0xC2, 0x45, 0xE4, 0x85, 0xB5, 0x76, 0x62, 0x5E, 0x7E, 0xC6, 0xF4, 0x4C, 0x42, 0xE9,
    0xA6, 0x37, 0xED, 0x6B, 0x0B, 0xFF, 0x5C, 0xB6, 0xF4, 0x06, 0xB7, 0xED, 0xEE, 0x38,
    0x6B, 0xFB, 0x5A, 0x89, 0x9F, 0xA5, 0xAE, 0x9F, 0x24, 0x11, 0x7C, 0x4B, 0x1F, 0xE6,
    0x49, 0x28, 0x66, 0x51, 0xEC, 0xE6, 0x53, 0x81, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF,
    0xFF, 0xFF
)
DH_PRIME_1024 = int.from_bytes(DH_PRIME_1024_BYTES, "big")

class DHSession:
    def __init__(self, client_pub_bytes):
        self.priv = int.from_bytes(os.urandom(128), "big")
        self.pub = pow(2, self.priv, DH_PRIME_1024)
        client_pub = int.from_bytes(client_pub_bytes, "big")
        shared = pow(client_pub, self.priv, DH_PRIME_1024).to_bytes(128, "big")
        salt = b"\x00" * 32
        prk = hmac.new(salt, shared, hashlib.sha256).digest()
        self.aes_key = hmac.new(prk, b"\x01", hashlib.sha256).digest()[:16]

    def encrypt(self, plain_bytes):
        pad_len = 16 - (len(plain_bytes) % 16)
        padded = plain_bytes + bytes([pad_len] * pad_len)
        iv = os.urandom(16)
        cipher = Cipher(algorithms.AES(self.aes_key), modes.CBC(iv), default_backend())
        enc = cipher.encryptor()
        return iv, enc.update(padded) + enc.finalize()

sessions = {}

class SecretService(dbus.service.Object):
    def __init__(self, bus, token_bytes):
        self.bus = bus
        self.token_bytes = token_bytes
        self.session_count = 0
        self.item_path = "/org/freedesktop/secrets/collection/login/1"
        self.collection_path = "/org/freedesktop/secrets/collection/login"
        super().__init__(bus, "/org/freedesktop/secrets")

    @dbus.service.method("org.freedesktop.Secret.Service", in_signature="sv", out_signature="vo")
    def OpenSession(self, algorithm, input_val):
        self.session_count += 1
        spath = f"/org/freedesktop/secrets/session/{self.session_count}"
        if algorithm == "plain":
            sessions[spath] = None
            return (dbus.ByteArray(b""), dbus.ObjectPath(spath))
        elif algorithm == "dh-ietf1024-sha256-aes128-cbc-pkcs7":
            client_pub = bytes(input_val)
            dh_sess = DHSession(client_pub)
            sessions[spath] = dh_sess
            server_pub_bytes = dh_sess.pub.to_bytes(128, "big")
            return (dbus.ByteArray(server_pub_bytes), dbus.ObjectPath(spath))
        else:
            raise dbus.exceptions.DBusException(f"Unsupported algorithm: {algorithm}")

    @dbus.service.method("org.freedesktop.Secret.Service", in_signature="s", out_signature="o")
    def ReadAlias(self, name):
        return dbus.ObjectPath(self.collection_path)

    @dbus.service.method("org.freedesktop.Secret.Service", in_signature="a{ss}", out_signature="aoao")
    def SearchItems(self, attributes):
        return ([dbus.ObjectPath(self.item_path)], [])

    @dbus.service.method("org.freedesktop.Secret.Service", in_signature="aoo", out_signature="a{o(oayays)}")
    def GetSecrets(self, items, session):
        res = {}
        dh_sess = sessions.get(str(session))
        if dh_sess is not None:
            iv, enc = dh_sess.encrypt(self.token_bytes)
        else:
            iv, enc = b"", self.token_bytes

        for item in items:
            res[item] = (
                dbus.ObjectPath(session),
                dbus.ByteArray(iv),
                dbus.ByteArray(enc),
                "text/plain"
            )
        return res

    @dbus.service.method("org.freedesktop.Secret.Service", in_signature="ao", out_signature="aoo")
    def Unlock(self, objects):
        return (objects, dbus.ObjectPath("/"))

    @dbus.service.method("org.freedesktop.Secret.Service", in_signature="ao", out_signature="aoo")
    def Lock(self, objects):
        return (objects, dbus.ObjectPath("/"))

class BaseCollection(dbus.service.Object):
    def __init__(self, bus, path, service):
        self.service = service
        super().__init__(bus, path)

    @dbus.service.method("org.freedesktop.Secret.Collection", in_signature="a{ss}", out_signature="ao")
    def SearchItems(self, attributes):
        return [dbus.ObjectPath(self.service.item_path)]

    @dbus.service.method("org.freedesktop.DBus.Properties", in_signature="ss", out_signature="v")
    def Get(self, interface_name, property_name):
        if property_name == "Label":
            return dbus.String("Default", variant_level=1)
        if property_name == "Locked":
            return dbus.Boolean(False, variant_level=1)
        if property_name == "Items":
            return dbus.Array([dbus.ObjectPath(self.service.item_path)], signature="o", variant_level=1)
        return dbus.String("", variant_level=1)

    @dbus.service.method("org.freedesktop.DBus.Properties", in_signature="s", out_signature="a{sv}")
    def GetAll(self, interface_name):
        return {
            "Label": dbus.String("Default", variant_level=1),
            "Locked": dbus.Boolean(False, variant_level=1),
            "Items": dbus.Array([dbus.ObjectPath(self.service.item_path)], signature="o", variant_level=1)
        }

class SecretItem(dbus.service.Object):
    def __init__(self, bus, service):
        self.service = service
        super().__init__(bus, "/org/freedesktop/secrets/collection/login/1")

    @dbus.service.method("org.freedesktop.Secret.Item", in_signature="o", out_signature="(oayays)")
    def GetSecret(self, session):
        dh_sess = sessions.get(str(session))
        if dh_sess is not None:
            iv, enc = dh_sess.encrypt(self.service.token_bytes)
        else:
            iv, enc = b"", self.service.token_bytes

        return (
            dbus.ObjectPath(session),
            dbus.ByteArray(iv),
            dbus.ByteArray(enc),
            "text/plain"
        )

    @dbus.service.method("org.freedesktop.DBus.Properties", in_signature="ss", out_signature="v")
    def Get(self, interface_name, property_name):
        if property_name == "Attributes":
            return dbus.Dictionary({"service": "gemini", "username": "antigravity"}, signature="ss", variant_level=1)
        if property_name == "Label":
            return dbus.String("Password for 'antigravity' on 'gemini'", variant_level=1)
        if property_name == "Locked":
            return dbus.Boolean(False, variant_level=1)
        return dbus.String("", variant_level=1)

    @dbus.service.method("org.freedesktop.DBus.Properties", in_signature="s", out_signature="a{sv}")
    def GetAll(self, interface_name):
        return {
            "Attributes": dbus.Dictionary({"service": "gemini", "username": "antigravity"}, signature="ss", variant_level=1),
            "Label": dbus.String("Password for 'antigravity' on 'gemini'", variant_level=1),
            "Locked": dbus.Boolean(False, variant_level=1)
        }

def main():
    token_file = sys.argv[1] if len(sys.argv) > 1 else os.path.expanduser("~/.gemini/keyring_token.json")
    with open(token_file, "rb") as f:
        token_bytes = f.read().strip()

    dbus.mainloop.glib.DBusGMainLoop(set_as_default=True)
    bus = dbus.SessionBus()
    bus_name = dbus.service.BusName("org.freedesktop.secrets", bus)

    srv = SecretService(bus, token_bytes)
    col1 = BaseCollection(bus, "/org/freedesktop/secrets/collection/login", srv)
    col2 = BaseCollection(bus, "/org/freedesktop/secrets/aliases/default", srv)
    item = SecretItem(bus, srv)

    print("Mock Secret Service running on org.freedesktop.secrets", flush=True)
    loop = GLib.MainLoop()
    loop.run()

if __name__ == "__main__":
    main()
