class FakeSSMService:
    def __init__(self, *arg, **kwargs):
        pass

    def get_ssm_parameters(self, parameters_keys, *arg, **kwargs):
        return {parameter: f"test_value_{parameter}" for parameter in parameters_keys}

    def get_ssm_parameter(self, parameters_keys, *arg, **kwargs):
        return f"test_value_{parameters_keys[0]}"

    def update_ssm_parameter(self, *arg, **kwargs):
        pass


class FakePDSService:
    def __init__(self, *arg, **kwargs):
        pass

    def pds_request(self, *arg, **kwargs):
        pass
