import requests
from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView
from stellar_base import Keypair, Builder
from stellar_base.asset import Asset
from stellar_base.exceptions import HorizonError
from stellar_base.horizon import horizon_testnet
from stellar_base.memo import TextMemo
from stellar_base.operation import Payment
from stellar_base.transaction import Transaction
from stellar_base.transaction_envelope import TransactionEnvelope

friend_bot_url = "https://friendbot.stellar.org"
horizon = horizon_testnet()


class AccountList(APIView):
    permission_classes = (permissions.AllowAny,)

    def post(self, request):

        key_pair = Keypair.random()
        public_key = key_pair.address().decode("UTF-8")
        private_key = key_pair.seed().decode("UTF-8")

        response = requests.get(friend_bot_url, params={'addr': public_key})

        if response.ok:
            data = {
                'publicKey': public_key,
                'privateKey': private_key
            }
        else:
            data = response.json()

        return Response(data, status=status.HTTP_201_CREATED)


class IssueAsset(APIView):
    permission_classes = (permissions.AllowAny,)

    def post(self, request):
        issued_private_key = request.data.get('privateKey')
        issued_address = Keypair.from_seed(issued_private_key).address().decode("UTF-8")

        # Get public address for issuer's account based on his private key
        issuer_secret = 'SCBHQEGSNBTT4S7Y73YAF3M3JSVSTSNBGAVU5M4XVFGUF7664EUXQHFU'
        issuer_address = Keypair.from_seed(issuer_secret).address().decode("UTF-8")

        # Register these address to the network
        requests.get(url=friend_bot_url, params={'addr': issued_address})
        requests.get(url=friend_bot_url, params={'addr': issuer_address})

        asset = Asset('NewAsset', issuer_address)

        builder = Builder(secret=issued_private_key,
                          network="TESTNET").append_change_trust_op(asset_code=asset.code, asset_issuer=asset.issuer)
        builder.sign()
        response = builder.submit()

        return Response(response, status=status.HTTP_200_OK)


class SendPayment(APIView):
    permission_classes = (permissions.AllowAny,)

    def post(self, request):
        source_private_key = request.data.get('sourcePrivateKey')
        dest_address = request.data.get('destAddress')
        amount = request.data.get('amount', '0.0000001')
        source = Keypair.from_seed(source_private_key)
        source_address = source.address().decode('UTF-8')

        requests.get(url=friend_bot_url, params={'addr': source_address})
        requests.get(url=friend_bot_url, params={'addr': dest_address})

        # Create operations for transaction
        payment = Payment(destination=dest_address,
                          asset=Asset('XLM'),
                          amount=amount)
        memo = TextMemo('Transaction Memo')
        sequence = horizon.account(source_address).get('sequence')

        operations = [payment]

        try:
            transaction = Transaction(source=source_address,
                                      sequence=sequence,
                                      memo=memo,
                                      fee=100 * len(operations),
                                      operations=operations)
            envelope = TransactionEnvelope(tx=transaction, network_id="TESTNET")
            # Sign the sender
            envelope.sign(source)
            # Submit it to the network
            xdr = envelope.xdr()
            response = horizon.submit(xdr)

            return Response(response, status=status.HTTP_200_OK)
        except HorizonError as horizonError:
            return Response(horizonError.message, status=horizonError.status_code)
