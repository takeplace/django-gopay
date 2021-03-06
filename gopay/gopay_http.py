# -*- coding: utf-8 -*-
import requests
import const
import utils
from django.conf import settings

VERIFY_SSL = getattr(settings, 'GOPAY_VERIFY_SSL', False)

WRONG_STATUS_MSG = u'wrong response status code: %s, 200 expected'

class Payment(object):
    def __init__(self, secret=settings.GOPAY_SECRET):
        self.crypt = utils.Crypt(secret=secret)
        self.concat = utils.Concat(secret=secret)

    def create_payment(self, productName, variableSymbol, totalPriceInCents, paymentChannels=const.PAYMENT_METHODS):
        cmd = self._create_payment_cmd(productName, variableSymbol, totalPriceInCents, paymentChannels)
        payment_string = self.concat(utils.Concat.PAYMENT, cmd)
        cmd['encryptedSignature'] = self.crypt.encrypt(payment_string)
        cmd = utils.prefix_command_keys(cmd, const.PREFIX_CMD_PAYMENT)
        r = requests.post(const.GOPAY_NEW_PAYMENT_URL, data=cmd, verify=VERIFY_SSL)

        if r.status_code != 200:
            raise utils.ValidationException(WRONG_STATUS_MSG % r.status_code)
        utils.CommandsValidator(r.content).payment()

        response = utils.parse_xml_to_dict(r.content)
        #        print response
        return response['paymentSessionId']


    def verify_payment_status(self, paymentSessionId):
        """tells if the payment was successful or not, returns tuple (success, whole response)"""

        cmd = dict(eshopGoId=settings.GOPAY_ESHOP_GOID, paymentSessionId=paymentSessionId)
        concat_cmd = self.concat(utils.Concat.PAYMENT_STATUS, cmd)
        cmd['encryptedSignature'] = self.crypt.encrypt(concat_cmd)
        cmd = utils.prefix_command_keys(cmd, prefix=const.PREFIX_CMD_PAYMENT_RESULT)
        r = requests.post(const.GOPAY_PAYMENT_STATUS_URL, data=cmd, verify=VERIFY_SSL)
        #        print r.content
        if r.status_code != 200:
            raise utils.ValidationException(WRONG_STATUS_MSG % r.status_code)
        utils.CommandsValidator(r.content).payment_status()
        response = utils.parse_xml_to_dict(r.content)
        #        print response
        return response['sessionState'] == const.PAYMENT_DONE, response


    def payment_status_notification_validation(self, params):
        """ params is dict with GET params from GoPay, if signature is not OK, raises ValidationException """

        utils.CommandsValidator(xml_response=None, data=params).payment_notification()

    def _create_payment_cmd(self, productName, variableSymbol, totalPrice, paymentChannels):
        return {
            'successURL': settings.GOPAY_SUCCESS_URL,
            'failedURL': settings.GOPAY_FAILED_URL,
            'productName': productName,
            'eshopGoId': settings.GOPAY_ESHOP_GOID,
            'variableSymbol': variableSymbol,
            'totalPrice': totalPrice, # in cents
            'paymentChannels': ",".join(paymentChannels),
            }

    def get_redirect_url(self, paymentSessionId):
        return utils.create_redirect_url(paymentSessionId)

