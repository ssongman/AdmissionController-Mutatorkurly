from flask import Flask, request, jsonify
from pprint import pprint
import jsonpatch
import copy
import base64

app = Flask(__name__)


@app.route('/health')  
def health():  
    return "OK"


@app.route('/mutate', methods=['POST'])
def webhook():
    request_info = request.json
    request_info_object = request_info["request"]["object"]
    env = request_info_object["metadata"]["annotations"]["env"]
    print("env", env)
    # print(request_info_object)

    modified_info = copy.deepcopy(request_info)
    pprint(modified_info)
    modified_info_object = modified_info["request"]["object"]

    imageValidating = True
    for container_spec in modified_info_object["spec"]["template"]["spec"]["containers"]:
        print(
            "Let's check port of {}/{}... \n".format(modified_info_object["metadata"]["name"], container_spec['name']))
        if not check_image_name(env, container_spec):
            imageValidating = False
            imageValidatingReason = "deployment is not allowed"
            break
        # end if
    # end for

    if not imageValidating:
        admissionReview = {
            "apiVersion": "admission.k8s.io/v1",
            "kind": "AdmissionReview",
            "response": {
                "uid": request_info["request"]["uid"],
                "allowed": False,
                "status": {
                    "reason": imageValidatingReason
                }
            }
        }

        return jsonify(admissionReview)
    # end if

    patch = jsonpatch.JsonPatch.from_diff(request_info_object, modified_info_object)
    print("############## JSON Patch ############## ")
    pprint(str(patch))
    print('\n')

    if len(patch.patch) > 0:
        admissionReview = {
            "apiVersion": "admission.k8s.io/v1",
            "kind": "AdmissionReview",
            "response": {
                "uid": request_info["request"]["uid"],
                "allowed": True,
                "patchType": "JSONPatch",
                "patch": base64.b64encode(str(patch).encode()).decode()
            }
        }
    else:
        admissionReview = {
            "apiVersion": "admission.k8s.io/v1",
            "kind": "AdmissionReview",
            "response": {
                "uid": request_info["request"]["uid"],
                "allowed": True,
                "status": {
                    "reason": "Deployment is allowed"
                }
            }
        }
    # end if

    print("############## This data will be sent to k8s (admissionReview) ##############")
    pprint(admissionReview)
    print('\n')

    return jsonify(admissionReview)


def check_image_name(as_env, ad_container_spec):
    rtn = True
    image = ad_container_spec["image"]
    # image = 'kurlycorp.kr.dev/nginx:latest'
    image_seperate_index = image.find('/')
    if image_seperate_index < 0:
        if as_env == 'dev':
            imageNew = 'kurlycorp.kr.dev/' + image
            ad_container_spec['image'] = imageNew
            print('Image name is changed!\n\n')
            return True
        elif as_env == 'prod':
            return False
    image_prefix = image[:image_seperate_index]
    image_postfix = image[image_seperate_index + 1:]

    if as_env == 'dev':
        if not 'kurlycorp.kr.dev' == image_prefix:
            imageNew = 'kurlycorp.kr.dev/' + image_postfix
            ad_container_spec['image'] = imageNew
            print('Image name is changed!\n\n')
    if as_env == 'prod':
        if not 'kurlycorp.kr.prod' == image_prefix:
            rtn = False
            print('[Warning] deployment is not allowed!\n\n')

    return rtn


app.run(host='0.0.0.0', debug=True, ssl_context=('/run/secrets/tls/tls.crt', '/run/secrets/tls/tls.key'))
