import json
import email
import difflib


class JSONEmailMessageEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, email.message.Message):
            return {'__email.message.Message__': True, 'string': obj.as_string()}
        # Let the base class default method raise the TypeError
        return json.JSONEncoder.default(self, obj)


class JSONEmailMessageDecoder(json.JSONDecoder):
    def decode(self, s):
        dct = super().decode(s)
        if '__email.message.Message__' in dct:
            return email.message_from_string(dct['string'])
        return dct


def encodeEmailMessageToJSON(obj):
    if isinstance(obj, email.message.Message):
        return {'__email.message.Message__': True, 'string': obj.as_string()}
    raise TypeError(repr(obj) + " is not JSON serializable")


def decodeEmailMessageFromJSON(dct):
    if '__email.message.Message__' in dct:
        return email.message_from_string(dct['string'])
    return dct


if __name__ == "__main__":

    rawStr = b'X-Apparently-To: fergusonsa@yahoo.com; Fri, 28 Aug 2015 21:47:34 +0000\r\nReturn-Path: <Instant.Confirm@alaskating.com>\r\nX-YahooFilteredBulk: 102.192.228.217\r\nReceived-SPF: pass (domain of alaskating.com designates 102.192.228.217 as permitted sender)\r\nX-YMailISG: Gn1CEjoWLDtiUg5dByWM934INbE4B.lY7c.1Dlfy4qVJvs2i\r\n oAqxnkkwdo1KVL.z9I3at_EWIx_0OYFew8tihRSWHfG33LuQPrGrQCmrmNnZ\r\n 5nTRWFr1gSmzcr8unooBlKZ9RhjpvlBmsxG0TynMax02HNngloB7OPf7f_Re\r\n Pp.aCntTuAWF7av5GzI9mACegJKRnnMnvU5XLx7fbF7lomY5n6s1jfgElGg.\r\n cjd9NyeShtC0xJ9mRC315Ij8S1tXzUKeUffLCb_9oYs2tcrKGMQ4RaWY2qYF\r\n JhWQd4dyWu1fD3tQMvGnZbsacn83kr0V2fymZZlwxB1i4kFj6O33o_7EcofA\r\n q.ccLmOvpGAoysmI8_PK5uixpHkYvnabYcLgm10c0TsDZeAdWEwEh5.FunTi\r\n dHM2Ht8hNTZuYPCaqP4uwslZSxUmfB6ctc9Jo_lkB4vQDXJMghkPkX_nDA9O\r\n lqtRrVNtY1rfmzVafALXC6ytOmiYKQiF0YrXnPp_RdM3aL6XFBdVcACWLZOs\r\n eAQU0Q.FWDVtYza.KVDwpGiixAAwu1.m3L3jvhdKqsYCNdE_NNjeSvResgB2\r\n NX98JmeZHj0O_bDm8eVDYWNy15RF6Huou9onVZJ55477FUALIlBEcPQV_Zu.\r\n PnSsGAm4SD6e3OCxgyVv9.uepEiA8g2cq4n2uHfVZBnZgkTv0X4HYgS4fWSQ\r\n zr4DuY7L4_ZNdyrsJMC1.oEodJtluF9jl5Iu_IEEeWX7xT3PZIfY8YKD3Tbl\r\n hZMFMMMlWtOzGeC7HzMeKV6fZgo5D_DpeascYYnf14RoNgQPbm7RE5HxQN6X\r\n rzwIrZXRSuwbkKVJgyMmDJL3_2uewWerPK8GPR70idHKXbt7xcNlqbSXeulC\r\n 4tv2GjJa64f4Y_BZxaoHWFbeThjBmf1oxUGaaUxuFk6.0EuyiB5jD7S4cPki\r\n jQFbTrSW26aeMfYDjpWqt161wmS9cGtxP_hTRGSGsa2e3Ppv0wXX9ZnSTFsN\r\n Sqi_OucuAr2WkDybx8ma28a_x1IVApEYBzZqPlOzeW6TH7TNVCqRLcYy2yev\r\n 0UCvdwwa4OHd81mdSRlKxDqpPGbwhNquxAwNOwiEWf4k.Vq2SZDR9FEMd9mH\r\n LhyQa6jT2tHVEB7A8D9noDh3Y3cmj9P9zq5C9UPfscIfogKPy04hDL4q84bO\r\n lM8Mz.jfynvdiY2yqsHFlGISKMolUw_a5Qx2kbtC1Rc4XDQtggWXrTrzivSU\r\n ktwe36GRKZyH7WAatVnhquexa4XM9c1JVH0FH0I3vgzc.A2_09WlCdK.K_uz\r\n V9GsYkLl.1Y1.g1eQr1_Ju5b7MwdBjk20p1nkwUOxU2ooFZ02D7WEd7mdjxD\r\n O2jcCd3XFavMUz0Eo45beO5FQDC.YTKTcQFgR.quOfoT2vWoZkaenZvWi0Vj\r\n zj9.nqawQFrWFN0SQfKLpx1yDAzjz.M8JTncS95bNVvGjsi89KFitrBBJdUz\r\n NK07i9Eheal6BSTp1TInlWAR4iNoRyfNZjKSGvwXDapAnC5TRuEKWAj603su\r\n nz5_eGiwNg--\r\nX-Originating-IP: [102.192.228.217]\r\nAuthentication-Results: mta1146.mail.bf1.yahoo.com  from=; domainkeys=fail (bad syntax);  from=; dkim=neutral (no sig)\r\nReceived: from 127.0.0.1  (EHLO alaskating.com) (102.192.228.217)\r\n  by mta1146.mail.bf1.yahoo.com with SMTP; Fri, 28 Aug 2015 21:47:33 +0000\r\nDomainKey-Signature: a=rsa-sha1; c=nofws; d=alaskating.com; q=dns; s=default; \r\n h=mime-version:content-type:content-transfer-encoding:to:from:subject:da\r\n te:message-id:from:subject:date; \r\n b=fBN/1bytrD8K7yg1HdITihFxMArZnlXJtc76PrDkV09x3tYU3hWjVIs3WIW0cU6d+E2LgKN4\r\n 9tJL+BR5eLlPFm5KF3cQVmU4dXBXl46BFTC9AjjZbm9Zanhhf86SpftiJ5eI+qTUSRwdw9ML\r\n JOWmHut81IOzIjxtFVmunZoySgc=\r\nDKIM-Signature: v=1; a=rsa-sha256; c=relaxed/relaxed; d=alaskating.com; \r\n i=@alaskating.com; q=dns/txt; s=default; t=1440798429; \r\n bh=2zb/3z5uQ2b7UY9vHi10Dt/CnsBia4UXIkzq9CIYKz0=; h=MIME-Version : \r\n Content-Type : Content-Transfer-Encoding : To : From : Subject : Date : \r\n Message-ID : From : Subject : Date; \r\n b=W/Jhj9RC3ZftAwkMFQhDjXkQF4AyzZCpJvnJ3tXNPBMCZY7Eq2GKcOiQ7W2W4GIC9umTV2\r\n l4jdlT3sELf/frYIZYItWtz3L2TCqvf7TY8GlpCQR1JYEbsnQ6QtpsnvPRC7tR91KO/oAKs3\r\n HLZZYL8ab/NFwD4gwAMfST7tlzcS4=\r\nMIME-Version: 1.0\r\nContent-Type: text/html; charset="utf-8"\r\nContent-Transfer-Encoding: base64\r\nTo: fergusonsa@yahoo.com\r\nFrom: =?utf-8?b?IuKdruKdrldBUk5JTkfina/ina8iIDxJbnN0YW50LkNvbmZpcm1AYWxhc2th?=\r\n =?utf-8?b?dGluZy5jb20+?=\r\nSubject: =?utf-8?q?=E2=9A=A0=EF=B8=8E_A_Background_Check_on_You_-_28_Aug_2015_14?=\r\n =?utf-8?b?OjQ3OjA5IOKaoO+4jg==?=\r\nDate: Fri, 28 Aug 2015 14:47:09 -0700\r\nMessage-ID: <55DCDEBE-C2B1-41F5-B2EB-07001ED6D1AC@alaskating.com>\r\nContent-Length: 2555\r\n\r\nPGh0bWwgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzE5OTkveGh0bWwiPg0KPGJvZHk+DQo8Y2Vu\r\ndGVyPg0KCTxmb3JtIG1ldGhvZD0iZ2V0IiBhY3Rpb249Imh0dHA6Ly9hbGFza2F0aW5nLmNvbS95\r\nZXlKaklqb2dNVEkzT1RVc0lDSm1Jam9nTUN3Z0ltMGlPaUF4TVRRME9Td2dJbXdpT2lBeU55d2dJ\r\nbk1pT2lBd0xDQWlkU0k2SURFMk1qQTBOekExT0N3Z0luUWlPaUF4TENBaWMyUWlPaUF3ZlE9PSI+\r\nDQoJCTxpbnB1dCB0eXBlPSJzdWJtaXQiIHZhbHVlPSLimqDvuI4gQSBCYWNrZ3JvdW5kIENoZWNr\r\nIG9uIFlvdSAtIDI4IEF1ZyAyMDE1IDE0OjQ3OjA5IOKaoO+4jiIgc3R5bGU9ImN1cnNvcjogcG9p\r\nbnRlcjtmb250LXNpemU6MjBweDsgYm9yZGVyLXJhZGl1czogNXB4OyBmb250LWZhbWlseToiVHJl\r\nYnVjaGV0IE1TIiwgSGVsdmV0aWNhLCBzYW5zLXNlcmlmIi8+DQoJPC9mb3JtPg0KPGJyLz4NCjxi\r\nci8+DQo8YnIvPg0KCTxtYXAgbmFtZT0ibV9mNmUxNmEwYTRiNTMxMWU1YWExNDQ0MWVhMTQ2NDY4\r\nNiI+DQoJICA8YXJlYSBzaGFwZT0icmVjdCIgY29vcmRzPSIwLDAsNjQ0LDY5NCIgYWx0PSIiIGhy\r\nZWY9Imh0dHA6Ly9hbGFza2F0aW5nLmNvbS95ZXlKaklqb2dNVEkzT1RVc0lDSm1Jam9nTUN3Z0lt\r\nMGlPaUF4TVRRME9Td2dJbXdpT2lBeU55d2dJbk1pT2lBd0xDQWlkU0k2SURFMk1qQTBOekExT0N3\r\nZ0luUWlPaUF4TENBaWMyUWlPaUF3ZlE9PSI+DQoJPC9tYXA+DQoJPGRpdiBzdHlsZT0iYmFja2dy\r\nb3VuZDogI2VlZTt3aWR0aDogNjQ0cHg7aGVpZ2h0OiA2OTRweDsgbWFyZ2luOiAwcHggYXV0bzsi\r\nPg0KCQk8aW1nIHA9IjIiIHNyYz0iaHR0cDovL2FsYXNrYXRpbmcuY29tLzFmZGJhMjE1MjJiZDRl\r\nYTFhMWE5YzQ5NDFhOTc1MGY2IiBib3JkZXI9IjAiIHVzZW1hcD0iI21fZjZlMTZhMGE0YjUzMTFl\r\nNWFhMTQ0NDFlYTE0NjQ2ODYiIC8+DQoJPC9kaXY+DQoJPGJyIC8+DQoJPGEgaHJlZj0iaHR0cDov\r\nL2FsYXNrYXRpbmcuY29tL3ZleUpqSWpvZ01USTNPVFVzSUNKbUlqb2dNQ3dnSW0waU9pQXhNVFEw\r\nT1N3Z0ltd2lPaUF5Tnl3Z0luTWlPaUF3TENBaWRTSTZJREUyTWpBME56QTFPQ3dnSW5RaU9pQXlM\r\nQ0FpYzJRaU9pQXdmUT09Ij4NCgkJPGltZyBwPSIzIiBzcmM9Imh0dHA6Ly9hbGFza2F0aW5nLmNv\r\nbS8wZjE5MDNiMjg1Zjg0MDA2YThhM2JmOWNiOTVmNDJmYyIgYm9yZGVyPSIwIiAvPg0KCTwvYT4N\r\nCgkNCgk8YnIvPg0KCTxici8+DQoJPGJyLz4NCgk8ZGl2IGFsaWduPSJjZW50ZXIiPg0KCQlJZiB5\r\nb3UgY2Fubm90IGNsaWNrIHRoZSBsaW5rIGFib3ZlLCBDb3B5ICYgUGFzdGUgdGhpcyBsaW5rOjxi\r\nci8+DQoJCWh0dHA6Ly9hbGFza2F0aW5nLmNvbS95ZXlKaklqb2dNVEkzT1RVc0lDSm1Jam9nTUN3\r\nZ0ltMGlPaUF4TVRRME9Td2dJbXdpT2lBeU55d2dJbk1pT2lBd0xDQWlkU0k2SURFMk1qQTBOekEx\r\nT0N3Z0luUWlPaUF4TENBaWMyUWlPaUF3ZlE9PQ0KCTwvZGl2Pg0KDQoJPGltZyBwPSIxIiBzcmM9\r\nImh0dHA6Ly9hbGFza2F0aW5nLmNvbS95ZXlKaklqb2dNVEkzT1RVc0lDSm1Jam9nTUN3Z0ltMGlP\r\naUF4TVRRME9Td2dJbXdpT2lBeU55d2dJbk1pT2lBd0xDQWlkU0k2SURFMk1qQTBOekExT0N3Z0lu\r\nUWlPaUF6TENBaWMyUWlPaUF3ZlE9PSIgYm9yZGVyPSIwIiAvPg0KPC9jZW50ZXI+DQo8L2JvZHk+\r\nDQo8L2h0bWw+DQo8Y2VudGVyPjxhIGhyZWY9Imh0dHA6Ly9hbGFza2F0aW5nLmNvbS8xZXlKaklq\r\nb2dNVEkzT1RVc0lDSnRJam9nTVRFME5Ea3NJQ0pzSWpvZ01qY3NJQ0p6SWpvZ05ESXNJQ0oxSWpv\r\nZ01UWXlNRFEzTURVNExDQWlkQ0k2SUNJaWZRPT0iID48aW1nIHNyYz0iaHR0cDovL2FsYXNrYXRp\r\nbmcuY29tLzAxMTdiODljMmRkNDExZTQ4ZDA5M2M0YTkyZGIwN2NlIiBib3JkZXI9IjAiLz48L2E+\r\nPC9jZW50ZXI+\r\n\r\n'
    msgFromBytes = email.message_from_bytes(rawStr)
    print('Message created from bytes: \n{}\n'.format(msgFromBytes.as_string()))
    jsonMsgClass = json.dumps(msgFromBytes, cls=JSONEmailMessageEncoder)
    print('\nJSON Encoded Email message: ')
    print(jsonMsgClass)
    msgFromJsonClass = json.loads(jsonMsgClass, cls=JSONEmailMessageDecoder)
    print('Message created from JSON string: \n{}\n'.format(msgFromJsonClass.as_string()))
    print('\nJSON Encoded Email message from JSON dumped Email: ')
    jsonMsgClass2 = json.dumps(msgFromJsonClass, cls=JSONEmailMessageEncoder)
    print(jsonMsgClass2)

    stringsSame = msgFromBytes.as_string() == msgFromJsonClass.as_string()
    print('\nIs the string of the msgFromBytes the same as msgFromJson: {}\n'.format('True' if stringsSame else 'False'))
    if not stringsSame:
        print('\n Diffs between msgFromBytes and msgFromJsonClass:')
        for line in difflib.context_diff(msgFromBytes.as_string().splitlines(), msgFromJsonClass.as_string().splitlines(), fromfile='MsgFromBytes', tofile='MsgFromJSON'):
            print(line)

    print('\n+++++++++++++++++++++++++++++++++++++\n\nJSON Encoded Email message: ')
    jsonMsgFunction = json.dumps(msgFromBytes, default=encodeEmailMessageToJSON)
    print(jsonMsgFunction)
    msgFromJsonFunction = json.loads(jsonMsgFunction, object_hook=decodeEmailMessageFromJSON)
    print('Message created from JSON string: \n{}\n'.format(msgFromJsonFunction.as_string()))
    print('\nJSON Encoded Email message from JSON dumped Email: ')
    jsonMsgFunction2 = json.dumps(msgFromJsonFunction, default=encodeEmailMessageToJSON)
    print(jsonMsgFunction2)

    stringsSame = msgFromBytes.as_string() == msgFromJsonFunction.as_string()
    print('\nIs the string of the msgFromBytes the same as msgFromJsonFunction: {}\n'.format('True' if stringsSame else 'False'))
    if not stringsSame:
        print('\n Diffs between msgFromBytes and msgFromJsonFunction:')
        for line in difflib.context_diff(msgFromBytes.as_string().splitlines(), msgFromJsonFunction.as_string().splitlines(), fromfile='MsgFromBytes', tofile='MsgFromJSON'):
            print(line)

    stringsSame = msgFromJsonClass.as_string() == msgFromJsonFunction.as_string()
    print('\nIs the string of the msgFromJsonClass the same as msgFromJsonFunction: {}\n'.format('True' if stringsSame else 'False'))
    if not stringsSame:
        print('\n Diffs between msgFromBytes and msgFromJsonFunction:')
        for line in difflib.context_diff(msgFromBytes.as_string().splitlines(), msgFromJsonFunction.as_string().splitlines(), fromfile='MsgFromBytes', tofile='MsgFromJSON'):
            print(line)
