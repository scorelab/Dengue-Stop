# importing models for flask-migrate to realize models and create tables according to models
from models.admin import Admin, admin_schema, admins_schema
from models.alert import Alert, alert_schema, alerts_schema
from models.event_status import EventStatus, event_status_schema, event_statuses_schema
from models.event import Event, event_schema, events_schema, event_with_full_schema, events_with_full_schema
from models.incident import Incident, incident_schema, incidents_schema, incident_with_user_schema, incidents_with_user_schema
from models.org_unit import OrgUnit, org_unit_schema, org_units_schema
from models.patient_status import PatientStatus, patient_status_schema, patient_statuses_schema
from models.user import User, user_schema, users_schema
from models.province import Province, province_schema, provinces_schema
from models.district import District, district_schema, districts_schema
from flask import Flask, request, jsonify, make_response
from flask_migrate import Migrate
from flask_cors import CORS
from sqlalchemy.sql import func
from database import db
from database import ma
import jwt
from datetime import datetime, timezone
import calendar
import bcrypt
from dateutil.relativedelta import relativedelta
import os
import datetime as dt

# init app
app = Flask(__name__)
CORS(app)
basedir = os.path.abspath(os.path.dirname(__file__))
# database
# to supress the warning on the terminal, specify this line
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql://root:test1234@localhost/dengue_stop'
SECRET_KEY = "thisisasecretkeythatmustbechangedlater"
# init extensions
db.init_app(app)
ma.init_app(app)
migrate = Migrate(app, db)

# @app.route('/pre_populate_database', methods=['POST'])
# ########## IMPORTANT!!! ##########
# # ONLY TO BE RUN ONCE TO POPULATE THE DATABASE AFTER INITIAL CREATION
# # ONCE THE POPULATION IS DONE. MAKE SURE TO COMMENT OR REMOVE THIS ENDPOINT
# # BEFORE RUNNING THIS ENDPOINT MAKE SURE TO PROPERLY ADD DATA NEEDED FOR PREPOPULAITON
# def pre_populate_database():
#     Province.prePopulateProvince()
#     District.prePopulateDistrict()
#     PatientStatus.prePopulatePatientStatus()
#     EventStatus.prePopulateEventStatus()
#     OrgUnit.prePopulateOrgUnit()
#     Admin.prePopulateAdminUser()

def authenticate_token(token):
    try:
        # removing bearer value
        tokenValue = token.split(" ")[1]
        payload = jwt.decode(tokenValue, SECRET_KEY)
        return(payload)
    except jwt.ExpiredSignatureError:
        print('Signature expired. Please log in again.')
        return False
    except jwt.InvalidTokenError:
        print('Invalid token. Please log in again.')
        return False


@app.route('/create_user', methods=['POST'])
def create_user():
    try:
        telephone = request.json['telephone']
        first_name = request.json['firstName']
        last_name = request.json['lastName']
        nic_number = request.json['nicNumber']
        email = request.json['email']
        password = request.json['password'].encode("utf-8")
        hashed_password = bcrypt.hashpw(password, bcrypt.gensalt())
        salt = request.json['salt']
        new_user = User(telephone, first_name, last_name,
                        nic_number, email, hashed_password, salt)
        db.session.add(new_user)
        db.session.commit()
        return user_schema.jsonify(new_user)

    except IOError:
        print("I/O error")
    except ValueError:
        print("Value Error")
    except:
        print("Unexpected error")
        raise

@app.route('/login_user', methods=['POST'])
def login_user():
    try:
        username = request.json['username']
        password = request.json['password']
        # selecting data without the password and salt as they are not required for the user session
        current_user = User.query.filter_by(telephone=username).first()
        db.session.commit()
        result = user_schema.dump(current_user)
        if(result != {}):
            # checking whether the hashed password matches the database
            if(bcrypt.checkpw(password.encode("utf-8"), result['password'].encode("utf-8"))):
                # returning a jwt to the app
                secret_key = SECRET_KEY
                token = jwt.encode({'user': username, 'userId': result['id'], 'exp': dt.datetime.utcnow(
                ) + dt.timedelta(hours=1)}, secret_key)
                userData = {'id': result['id'], 'first_name': result['first_name'], 'last_name': result['last_name'],
                            'email': result['email'], 'telephone': result['telephone'], 'nic_number': result['nic_number']}
                return jsonify({'token': token.decode('UTF-8'), 'userData': userData})
        # returning 401 error to the app
        return make_response('Could Not Authenticate', 401)

    except IOError:
        print("I/O error")
    except ValueError:
        print("Value Error")
    except:
        print("Unexpected error")
        raise


@ app.route('/get_user_salt', methods=['POST'])
def get_user_salt():
    # user will get their salt to generate the hash required to the provided password
    try:
        username = request.json['username']
        user_hash = User.query.with_entities(User.salt).filter_by(
            telephone=username).first()
        db.session.commit()
        result = user_schema.dump(user_hash)
        if(result != {}):
            return jsonify(result)
        return make_response('User Not Found', 404)

    except IOError:
        print("I/O error")
    except ValueError:
        print("Value Error")
    except:
        print("Unexpected error")
        raise

@app.route('/update_user', methods=['POST'])
def update_user():
    # checking for authentication
    auth_res = authenticate_token(request.headers['authorization'])
    if(auth_res != False):
        try:
            user_id = request.json['id']
            if (auth_res['userId'] == user_id):
                first_name = request.json['firstName']
                last_name = request.json['lastName']
                nic_number = request.json['nicNumber']
                email = request.json['email']
                updated_user = User.query.filter_by(id=user_id).first()
                updated_user.first_name = first_name
                updated_user.last_name = last_name
                updated_user.nic_number = nic_number
                updated_user.email = email
                db.session.merge(updated_user)
                db.session.commit()
                return user_schema.jsonify(updated_user)

        except IOError:
            print("I/O error")
        except ValueError:
            print("Value Error")
        except:
            print("Unexpected error")
            raise

    return make_response('Request Forbidden', 403)

@app.route('/report_incident', methods=['POST'])
# endpoint to add a new report
def report_incident():
    # checking for authentication
    auth_res = authenticate_token(request.headers['authorization'])
    if(auth_res != False):
        try:
            user_id = request.json['reportedUserId']
            if (auth_res['userId'] == user_id):
                province = request.json['province']
                district = request.json['district']
                city = request.json['city']
                location_lat = request.json['locationLat']
                location_long = request.json['locationLong']
                patient_name = request.json['patientName']
                patient_gender = request.json['patientGender']
                patient_dob = request.json['patientDob']
                description = request.json['description']
                reported_user_id = request.json['reportedUserId']
                patient_status_id = request.json['patientStatusId']
                is_verified = request.json['isVerified']
                verified_by = request.json['verifiedBy']
                org_id = request.json['orgId']
                new_incident = Incident(province, district, city, location_lat, location_long, patient_name, patient_gender,
                                        patient_dob, description, reported_user_id, patient_status_id, is_verified, verified_by, org_id)
                db.session.add(new_incident)
                db.session.commit()
                return incident_schema.jsonify(new_incident)

        except IOError:
            print("I/O error")
        except ValueError:
            print("Value Error")
        except:
            print("Unexpected error")
            raise

    return make_response('Request Forbidden', 403)

@ app.route('/get_incidents_by_user/<int:user_id>', methods=['GET'])
def get_incidents_by_user(user_id):
    # checking for authentication
    auth_res = authenticate_token(request.headers['authorization'])
    if(auth_res != False and (auth_res['userId'] == user_id)):
        # returns all the incidents that was reported by the user of the user_id
        incidents = Incident.query.filter_by(
            reported_user_id=user_id).order_by(Incident.reported_time.desc()).all()
        db.session.commit()
        result = incidents_schema.dump(incidents)
        return jsonify(result)
    else:
        return make_response('Request Forbidden', 403)

@ app.route('/get_provinces', methods=['GET'])
def get_provinces():
    # checking for authentication
    auth_res = authenticate_token(request.headers['authorization'])
    if(auth_res != False):
        # returns all the provinces in the db
        provinces = Province.query.all()
        db.session.commit()
        result = provinces_schema.dump(provinces)
        return jsonify(result)
    else:
        return make_response('Request Forbidden', 403)
        

@ app.route('/get_districts', methods=['GET'])
def get_districts():
    # checking for authentication
    auth_res = authenticate_token(request.headers['authorization'])
    if(auth_res != False):
        # returns all the procinces in the db
        districts = District.query.all()
        db.session.commit()
        result = districts_schema.dump(districts)
        return jsonify(result)
    else:
        return make_response('Request Forbidden', 403)

      
@ app.route('/get_patient_status_list', methods=['GET'])
def get_patient_status_list():
    # checking for authentication
    auth_res = authenticate_token(request.headers['authorization'])
    if(auth_res != False):
        # returns all the procinces in the db
        patientStatus = PatientStatus.query.all()
        db.session.commit()
        result = patient_statuses_schema.dump(patientStatus)
        return jsonify(result)
    else:
        return make_response('Request Forbidden', 403)
        

@ app.route('/get_org_unit/<province>/<district>', methods=['GET'])
def get_incident_org_unit(province, district):
    # checking for authentication
    auth_res = authenticate_token(request.headers['authorization'])
    if(auth_res != False):
        # returns all the procinces in the db
        orgUnit = OrgUnit.query.filter_by(
            province=province, district=district).first()
        db.session.commit()
        result = org_unit_schema.dump(orgUnit)
        return jsonify(result)
    else:
        return make_response('Request Forbidden', 403)


@ app.route('/get_pending_incidents_by_org/<org_id>', methods=['GET'])
def get_pending_incidents_by_org(org_id):
    # checking for authentication
    auth_res = authenticate_token(request.headers['authorization'])
    if(auth_res != False):
        # returns all the incidents related to the org
        incidents = db.session.query(Incident, User, PatientStatus).filter_by(org_id=org_id).filter_by(is_verified=0).join(User).join(PatientStatus).order_by(Incident.reported_time.desc()).all()
        db.session.commit()
        # converting the query response to the expected schema
        result = incidents_with_user_schema.dump([{'incident': x[0], 'user': x[1], 'status': x[2]} for x in incidents])
        return jsonify(result)
    else:
        return make_response('Request Forbidden', 403)


@ app.route('/verify_incident/<incident_id>/<verified_admin_id>', methods=['GET'])
def verify_incident(incident_id, verified_admin_id):
     # checking for authentication
    auth_res = authenticate_token(request.headers['authorization'])
    if(auth_res != False):
        try:
            updateIncident = Incident.query.filter_by(id=incident_id).first()
            if(updateIncident != {}):
                # now the incident is verified
                updateIncident.is_verified = 1
                # updating the verified admin ID
                updateIncident.verified_by = verified_admin_id
                # change patient status to status 2 - pending treatment
                updateIncident.patient_status_id = 2
                db.session.commit()
                return make_response('Incident Verified', 200)
            return make_response('Incident Not Found', 404)

        except IOError:
            print("I/O error")
        except ValueError:
            print("Value Error")
        except:
            print("Unexpected error")
            raise
    else:
        return make_response('Request Forbidden', 403)

@ app.route('/decline_incident/<incident_id>/<verified_admin_id>', methods=['GET'])
def decline_incident(incident_id, verified_admin_id):
    # checking for authentication
    auth_res = authenticate_token(request.headers['authorization'])
    if(auth_res != False):
        try:
            updateIncident = Incident.query.filter_by(id=incident_id).first()
            if(updateIncident != {}):
                # now the incident is declined
                updateIncident.is_verified = 2
                # updating the verified admin ID
                updateIncident.verified_by = verified_admin_id
                # change patient status to status 7 - declined
                updateIncident.patient_status_id = 7
                db.session.commit()
                return make_response('Incident Declined', 200)
            return make_response('Incident Not Found', 404)

        except IOError:
            print("I/O error")
        except ValueError:
            print("Value Error")
        except:
            print("Unexpected error")
            raise
    else:
        return make_response('Request Forbidden', 403)


@ app.route('/get_total_incident_summary', methods=['GET'])
def get_total_incident_summary():
    # checking for authentication
    auth_res = authenticate_token(request.headers['authorization'])
    if(auth_res != False):
        try:
            # groups VERIFIED incidents by province and counts them and returns their numbers
            # we only consider patient who are currently suffering with disease recovered patients are disregarded
            incident_by_province_count = db.session.query(Incident.province, func.count(Incident.province)).filter(Incident.patient_status_id > 1, Incident.patient_status_id < 5).group_by(Incident.province).all()
            db.session.commit()
            if(incident_by_province_count != {}):
                return jsonify(incident_by_province_count)
            return make_response('Count Not Found', 404)

        except IOError:
            print("I/O error")
        except ValueError:
            print("Value Error")
        except:
            print("Unexpected error")
            raise
    else:
        return make_response('Request Forbidden', 403)


@ app.route('/get_events_by_org/<org_id>', methods=['GET'])
def get_events_by_org(org_id):
    # checking for authentication
    auth_res = authenticate_token(request.headers['authorization'])
    if(auth_res != False):
        try:
            # get all events of the organization
            events = db.session.query(Event, Admin, EventStatus).filter_by(org_id=org_id).join(Admin).join(EventStatus).order_by(Event.start_time.desc()).all()
            db.session.commit()
            if(events != {}):
                result = events_with_full_schema.dump([{'event': x[0], 'admin': x[1], 'status': x[2]} for x in events])
                return jsonify(result)
            return make_response('Count Not Found', 404)

        except IOError:
            print("I/O error")
        except ValueError:
            print("Value Error")
        except:
            print("Unexpected error")
            raise
    else:
        return make_response('Request Forbidden', 403)


@ app.route('/get_incident_markers_by_province/<province>', methods=['GET'])
def get_incident_markers_by_province(province):
    # checking for authentication
    auth_res = authenticate_token(request.headers['authorization'])
    if(auth_res != False):
        try:
            # we only consider patient who are currently suffering with disease recovered patients are disregarded
            if(province == "all"):
                # get all markers of the verified incidents
                markers = Incident.query.filter(Incident.patient_status_id > 1, Incident.patient_status_id < 5).with_entities(Incident.location_lat, Incident.location_long, Incident.district, Incident.patient_status_id).all()
                db.session.commit()
                if(markers != {}):
                    return jsonify(markers)
                return make_response('Markers Not Found', 404)
            else:
                markers = Incident.query.filter_by(province=province).filter(Incident.patient_status_id > 1, Incident.patient_status_id < 5).with_entities(Incident.location_lat, Incident.location_long, Incident.district, Incident.patient_status_id).all()
                db.session.commit()
                if(markers != {}):
                    return jsonify(markers)
                return make_response('Markers Not Found', 404)

        except IOError:
            print("I/O error")
        except ValueError:
            print("Value Error")
        except:
            print("Unexpected error")
            raise 
    else:
        return make_response('Request Forbidden', 403)


@ app.route('/get_province_names', methods=['GET'])
def get_province_names():
     # checking for authentication
    auth_res = authenticate_token(request.headers['authorization'])
    if(auth_res != False):
        try:
            # returns all the provinces in the db
            provinces = Province.query.order_by(Province.name.asc()).all()
            db.session.commit()
            if(provinces != {}):
                result = provinces_schema.dump(provinces)
                return jsonify(result)
            return make_response('Provinces Not Found', 404)

        except IOError:
            print("I/O error")
        except ValueError:
            print("Value Error")
        except:
            print("Unexpected error")
            raise 
    else:
        return make_response('Request Forbidden', 403)

@ app.route('/query_incidents', methods=['POST'])
def query_incidents():
    # checking for authentication
    auth_res = authenticate_token(request.headers['authorization'])
    if(auth_res != False):
        org_id = request.json['orgId']
        patient_name = request.json['patientName']
        province = request.json['province']
        status = request.json['status']
        date_range = request.json['dateRange']
        duration = datetime.utcnow()
        if(date_range == "weekly"):
            # setting the duration upto last week
            duration = duration - relativedelta(weeks=1)
        elif(date_range == "monthly"):
            # setting the duration upto last month
            duration = duration - relativedelta(months=1)
        elif(date_range == "yearly"):
            # setting the duration upto last year
            duration = duration - relativedelta(years=1)
        
        try:
            # returns all the incident of an organization based on the parameters provided
            if(date_range == "all"):
                # remove date range from the query
                if(status == "all"):
                    # remove patient status from the query
                    if(province == "all"):
                    # remove province from the query
                        if(patient_name == ""):
                            # remove patient name from the query
                            incidents = db.session.query(Incident, User, PatientStatus, Admin).filter(
                                Incident.org_id == org_id 
                                ).join(User).join(PatientStatus).join(Admin).order_by(Incident.reported_time.desc()).all()
                        else:
                            incidents = db.session.query(Incident, User, PatientStatus, Admin).filter(
                                Incident.patient_name.ilike("%"+patient_name+"%"),
                                Incident.org_id == org_id 
                                ).join(User).join(PatientStatus).join(Admin).order_by(Incident.reported_time.desc()).all()
                    else:
                        if(patient_name == ""):
                            # remove patient name from the query
                            incidents = db.session.query(Incident, User, PatientStatus, Admin).filter(
                                Incident.org_id == org_id, 
                                Incident.province == province, 
                                ).join(User).join(PatientStatus).join(Admin).order_by(Incident.reported_time.desc()).all()
                        else:
                            incidents = db.session.query(Incident, User, PatientStatus, Admin).filter(
                                Incident.patient_name.ilike("%"+patient_name+"%"),
                                Incident.org_id == org_id, 
                                Incident.province == province, 
                                ).join(User).join(PatientStatus).join(Admin).order_by(Incident.reported_time.desc()).all()
                else:
                    if(province == "all"):
                    # remove province from the query
                        if(patient_name == ""):
                            # remove patient name from the query
                            incidents = db.session.query(Incident, User, PatientStatus, Admin).filter(
                                Incident.org_id == org_id,
                                Incident.patient_status_id == status,
                                ).join(User).join(PatientStatus).join(Admin).order_by(Incident.reported_time.desc()).all()
                        else:
                            incidents = db.session.query(Incident, User, PatientStatus, Admin).filter(
                                Incident.patient_name.ilike("%"+patient_name+"%"),
                                Incident.org_id == org_id,
                                Incident.patient_status_id == status, 
                                ).join(User).join(PatientStatus).join(Admin).order_by(Incident.reported_time.desc()).all()
                    else:
                        if(patient_name == ""):
                            # remove patient name from the query
                            incidents = db.session.query(Incident, User, PatientStatus, Admin).filter(
                                Incident.org_id == org_id, 
                                Incident.province == province,
                                Incident.patient_status_id == status, 
                                ).join(User).join(PatientStatus).join(Admin).order_by(Incident.reported_time.desc()).all()
                        else:
                            incidents = db.session.query(Incident, User, PatientStatus, Admin).filter(
                                Incident.patient_name.ilike("%"+patient_name+"%"),
                                Incident.org_id == org_id, 
                                Incident.province == province, 
                                Incident.patient_status_id == status,
                                ).join(User).join(PatientStatus).join(Admin).order_by(Incident.reported_time.desc()).all()
            else:
                if(status == "all"):
                    # remove patient status from the query
                    if(province == "all"):
                    # remove province from the query
                        if(patient_name == ""):
                            # remove patient name from the query
                            incidents = db.session.query(Incident, User, PatientStatus, Admin).filter(
                                Incident.org_id == org_id,
                                Incident.reported_time >= duration 
                                ).join(User).join(PatientStatus).join(Admin).order_by(Incident.reported_time.desc()).all()
                        else:
                            incidents = db.session.query(Incident, User, PatientStatus, Admin).filter(
                                Incident.patient_name.ilike("%"+patient_name+"%"),
                                Incident.org_id == org_id,
                                Incident.reported_time >= duration 
                                ).join(User).join(PatientStatus).join(Admin).order_by(Incident.reported_time.desc()).all()
                    else:
                        if(patient_name == ""):
                            # remove patient name from the query
                            incidents = db.session.query(Incident, User, PatientStatus, Admin).filter(
                                Incident.org_id == org_id, 
                                Incident.province == province, 
                                Incident.reported_time >= duration
                                ).join(User).join(PatientStatus).join(Admin).order_by(Incident.reported_time.desc()).all()
                        else:
                            incidents = db.session.query(Incident, User, PatientStatus, Admin).filter(
                                Incident.patient_name.ilike("%"+patient_name+"%"),
                                Incident.org_id == org_id, 
                                Incident.province == province, 
                                Incident.reported_time >= duration
                                ).join(User).join(PatientStatus).join(Admin).order_by(Incident.reported_time.desc()).all()
                else:
                    # remove patient status from the query
                    if(province == "all"):
                    # remove province from the query
                        if(patient_name == ""):
                            # remove patient name from the query
                            incidents = db.session.query(Incident, User, PatientStatus, Admin).filter(
                                Incident.org_id == org_id,
                                Incident.patient_status_id == status,
                                Incident.reported_time >= duration
                                ).join(User).join(PatientStatus).join(Admin).order_by(Incident.reported_time.desc()).all()
                        else:
                            incidents = db.session.query(Incident, User, PatientStatus, Admin).filter(
                                Incident.patient_name.ilike("%"+patient_name+"%"),
                                Incident.org_id == org_id,
                                Incident.patient_status_id == status, 
                                Incident.reported_time >= duration
                                ).join(User).join(PatientStatus).join(Admin).order_by(Incident.reported_time.desc()).all()
                    else:
                        if(patient_name == ""):
                            # remove patient name from the query
                            incidents = db.session.query(Incident, User, PatientStatus, Admin).filter(
                                Incident.org_id == org_id, 
                                Incident.province == province,
                                Incident.patient_status_id == status,
                                Incident.reported_time >= duration 
                                ).join(User).join(PatientStatus).join(Admin).order_by(Incident.reported_time.desc()).all()
                        else:
                            incidents = db.session.query(Incident, User, PatientStatus, Admin).filter(
                                Incident.patient_name.ilike("%"+patient_name+"%"),
                                Incident.org_id == org_id, 
                                Incident.province == province, 
                                Incident.patient_status_id == status,
                                Incident.reported_time >= duration
                                ).join(User).join(PatientStatus).join(Admin).order_by(Incident.reported_time.desc()).all()

            db.session.commit()
            if(incidents != {}):
                result = incidents_with_user_schema.dump([{'incident': x[0], 'user': x[1], 'status': x[2], 'admin': x[3]} for x in incidents])
                return jsonify(result)
            return make_response('Incidents Not Found', 404)

        except IOError:
            print("I/O error")
        except ValueError:
            print("Value Error")
        except:
            print("Unexpected error")
            raise 
    else:
        return make_response('Request Forbidden', 403)

@ app.route('/get_patient_statuses', methods=['GET'])
def get_patient_statuses():
     # checking for authentication
    auth_res = authenticate_token(request.headers['authorization'])
    if(auth_res != False):
        # returns all the patient statuses in the db
        patientStatus = PatientStatus.query.order_by(PatientStatus.id.asc()).all()
        db.session.commit()
        if(patientStatus != {}):
            result = patient_statuses_schema.dump(patientStatus)
            return jsonify(result)
        return make_response('Patient Status Not Found', 404)
    else:
        return make_response('Request Forbidden', 403)

@ app.route('/update_patient_status/<incident_id>/<new_status>', methods=['GET'])
def update_patient_status(incident_id, new_status):
      # checking for authentication
    auth_res = authenticate_token(request.headers['authorization'])
    if(auth_res != False):
        # returns the incident related to the id provided
        try:
            updateIncident = Incident.query.filter_by(id=incident_id).first()
            if(updateIncident != {}):
                updateIncident.patient_status_id = new_status
                db.session.commit()
                return make_response('Patient Status Changed', 200)
            return make_response('Incident Not Found', 404)

        except IOError:
            print("I/O error")
        except ValueError:
            print("Value Error")
        except:
            print("Unexpected error")
            raise
    else:
        return make_response('Request Forbidden', 403)



@ app.route('/get_monthly_incident_count/<org_id>', methods=['GET'])
def get_monthly_incident_count(org_id):
    # checking for authentication
    auth_res = authenticate_token(request.headers['authorization'])
    if(auth_res != False):
        # returns the count of VERIFIED monthly incidents reported of the organization
        # this is used in metrics for visualization
        try:
            # initializing an array of 12 months with count 0
            duration = datetime.utcnow()
            duration = duration - relativedelta(years=1)
            monthlyCountArray = []
            for i in range(12):
                monthObj = {
                    # using calendar API to generate month names
                    "name": calendar.month_name[i+1],
                    "count": 0

                }
                monthlyCountArray.append(monthObj)

            monthlyCount = db.session.query(Incident.reported_time, func.count(Incident.reported_time)).filter(Incident.org_id==org_id, Incident.is_verified==1, Incident.reported_time >= duration).group_by(func.year(Incident.reported_time), func.month(Incident.reported_time)).all()
            db.session.commit()
            if(monthlyCount != {}):
                for x in monthlyCount:
                    # reducing 1 from the actual month to fit into monthlyCountArray index
                    monthIndex = x[0].month - 1
                    monthObj = {
                    # using calendar API to generate month names
                    "name": calendar.month_name[monthIndex+1],
                    "count": x[1]

                    }
                    # updating the count
                    monthlyCountArray[monthIndex] = monthObj
                return jsonify(monthlyCountArray)
            return make_response('Monthly Incident Count Not Found', 404)

        except IOError:
            print("I/O error")
        except ValueError:
            print("Value Error")
        except:
            print("Unexpected error")
            raise
    else:
        return make_response('Request Forbidden', 403)


@ app.route('/get_incident_age_group_count/<org_id>/<date_range>', methods=['GET'])
def get_incident_age_group_count(org_id, date_range):
     # checking for authentication
    auth_res = authenticate_token(request.headers['authorization'])
    if(auth_res != False):
        # returns the count of VERIFIED incidents age group count reported of the organization
        # this is used in metrics for visualization
        # age groups are as follow
        # 0-2 years = babies
        # 3-18 years = children
        # 19-35 years = young adults
        # 36-50 years = adults
        # 51 and above = elders
        try:
            # initializing an array of age groups with count 0
            duration = datetime.utcnow()
            if(date_range == "weekly"):
                # setting the duration upto last week
                duration = duration - relativedelta(weeks=1)
            elif(date_range == "monthly"):
                # setting the duration upto last month
                duration = duration - relativedelta(months=1)
            elif(date_range == "yearly"):
                # setting the duration upto last year
                duration = duration - relativedelta(years=1)
            ageCountArray = []
            currentYear = datetime.now().year
            babyCount = 0
            childrenCount = 0
            youngAdultCount = 0
            adultCount = 0
            seniorCount = 0
            ageCount = {}
            if(date_range == "all"):
                ageCount = db.session.query(Incident.patient_dob, func.count(Incident.patient_dob)).filter(Incident.org_id==org_id, Incident.is_verified==1).group_by(func.year(Incident.patient_dob)).all()
            else:
                ageCount = db.session.query(Incident.patient_dob, func.count(Incident.patient_dob)).filter(Incident.org_id==org_id, Incident.is_verified==1, Incident.reported_time >= duration).group_by(func.year(Incident.patient_dob)).all()
            db.session.commit()
            if(ageCount != {}):
                for x in ageCount:
                    # getting the current age of the patient
                    currentAge = currentYear - x[0].year 
                    if(currentAge > 0 and currentAge <=2):
                        babyCount += x[1]
                    elif(currentAge > 2 and currentAge <=18):
                        childrenCount += x[1]
                    elif(currentAge > 19 and currentAge <=35):
                        youngAdultCount += x[1]
                    elif(currentAge > 36 and currentAge <=50):
                        adultCount += x[1]
                    else:
                        seniorCount += x[1]

                ageCountArray.append({
                    "name": "Babies",
                    "range": "0 - 2 years",
                    "count": babyCount
                })
                ageCountArray.append({
                    "name": "Children",
                    "range": "3 - 18 years",
                    "count": childrenCount
                })
                ageCountArray.append({
                    "name": "Young Adults",
                    "range": "19 - 35 years",
                    "count": youngAdultCount
                })
                ageCountArray.append({
                    "name": "Adults",
                    "range": "36 - 50 years",
                    "count": adultCount
                })
                ageCountArray.append({
                    "name": "Seniors",
                    "range": "51 years and above",
                    "count": seniorCount
                })
                return jsonify(ageCountArray)
            return make_response('Age Incident Count Not Found', 404)

        except IOError:
            print("I/O error")
        except ValueError:
            print("Value Error")
        except:
            print("Unexpected error")
            raise
    else:
        return make_response('Request Forbidden', 403)


@ app.route('/get_incident_status_count/<org_id>/<date_range>', methods=['GET'])
def get_incident_status_count(org_id, date_range):
    # checking for authentication
    auth_res = authenticate_token(request.headers['authorization'])
    if(auth_res != False):
        # returns the count of VERIFIED incidents count according to the status of reported of the organization
        # this is used in metrics for visualization
        try:
            # this is for date range filtering
            duration = datetime.utcnow()
            if(date_range == "weekly"):
                # setting the duration upto last week
                duration = duration - relativedelta(weeks=1)
            elif(date_range == "monthly"):
                # setting the duration upto last month
                duration = duration - relativedelta(months=1)
            elif(date_range == "yearly"):
                # setting the duration upto last year
                duration = duration - relativedelta(years=1)
            # initializing array to count the incidents belong to a certain status
            statusCountArray = []
            pendingTreatmentCount = 0
            underTreatmentCount = 0
            recoveringCount = 0
            recoveredCount = 0
            deathCount = 0
            statusCount = {}
            if(date_range == "all"):
                statusCount = db.session.query(Incident.patient_status_id, func.count(Incident.patient_status_id)).filter(Incident.org_id==org_id, Incident.is_verified==1).group_by(Incident.patient_status_id).all()
            else:
                statusCount = db.session.query(Incident.patient_status_id, func.count(Incident.patient_status_id)).filter(Incident.org_id==org_id, Incident.is_verified==1, Incident.reported_time >= duration).group_by(Incident.patient_status_id).all()
            db.session.commit()
            if(statusCount != {}): 
                for x in statusCount:
                    status_id = x[0]
                    if(status_id == 2):
                        pendingTreatmentCount = x[1]
                    elif(status_id == 3):
                        underTreatmentCount = x[1]
                    elif(status_id == 4):
                        recoveringCount = x[1]
                    elif(status_id == 5):
                        recoveredCount = x[1]
                    elif(status_id ==6):
                        deathCount = x[1]

                statusCountArray.append({
                    "name": "Pending Treatment",
                    "count": pendingTreatmentCount
                })
                statusCountArray.append({
                    "name": "Under Treatment",
                    "count": underTreatmentCount
                })
                statusCountArray.append({
                    "name": "Recovering",
                    "count": recoveringCount
                })
                statusCountArray.append({
                    "name": "Recovered",
                    "count": recoveredCount
                })
                statusCountArray.append({
                    "name": "Death",
                    "count": deathCount
                })

                return jsonify(statusCountArray)
            return make_response('Status Incident Count Not Found', 404)

        except IOError:
            print("I/O error")
        except ValueError:
            print("Value Error")
        except:
            print("Unexpected error")
            raise
    else:
        return make_response('Request Forbidden', 403)


@ app.route('/get_incident_verification_breakdown/<org_id>/<date_range>', methods=['GET'])
def get_incident_verification_breakdown(org_id, date_range):
    # checking for authentication
    auth_res = authenticate_token(request.headers['authorization'])
    if(auth_res != False):
        # returns the count of incidents count according to their status in the organization
        # this is used in metrics for visualization
        try:
            # this is for date range filtering
            duration = datetime.utcnow()
            if(date_range == "weekly"):
                # setting the duration upto last week
                duration = duration - relativedelta(weeks=1)
            elif(date_range == "monthly"):
                # setting the duration upto last month
                duration = duration - relativedelta(months=1)
            elif(date_range == "yearly"):
                # setting the duration upto last year
                duration = duration - relativedelta(years=1)
            # initializing array to count the incidents belong to a certain status
            incidentBreakdownArray = []
            pendingIncidentCount = 0
            verifiedIncidentCount = 0
            declinedIncidentCount = 0
            incidentCount = {}
            if(date_range == "all"):
                incidentCount = db.session.query(Incident.is_verified, func.count(Incident.is_verified)).filter(Incident.org_id==org_id).group_by(Incident.is_verified).all()
            else:
                incidentCount = db.session.query(Incident.is_verified, func.count(Incident.is_verified)).filter(Incident.org_id==org_id, Incident.reported_time >= duration).group_by(Incident.is_verified).all()
            db.session.commit()
            if(incidentCount != {}): 
                for x in incidentCount:
                    verification = x[0]
                    if(verification == 0):
                        pendingIncidentCount = x[1]
                    elif(verification == 1):
                        verifiedIncidentCount = x[1]
                    elif(verification == 2):
                        declinedIncidentCount = x[1]

                incidentBreakdownArray.append({
                    "name": "Pending",
                    "count": pendingIncidentCount
                })
                incidentBreakdownArray.append({
                    "name": "Verified",
                    "count": verifiedIncidentCount
                })
                incidentBreakdownArray.append({
                    "name": "Declined",
                    "count": declinedIncidentCount
                })

                return jsonify(incidentBreakdownArray)
            return make_response('Incident Breakdown Not Found', 404)

        except IOError:
            print("I/O error")
        except ValueError:
            print("Value Error")
        except:
            print("Unexpected error")
            raise
    else:
        return make_response('Request Forbidden', 403)


@ app.route('/get_user_base_breakdown', methods=['GET'])
def get_user_base_breakdown():
    # checking for authentication
    auth_res = authenticate_token(request.headers['authorization'])
    if(auth_res != False):
        # returns the total number of admin and users in the system
        # this is used in metrics for visualization
        try:
            userBreakdownArray = []
            adminCount = -1
            userCount = -1
            userCount = db.session.query(User).count()
            adminCount = db.session.query(Admin).count()
            db.session.commit()
            if(userCount != -1 and adminCount != -1): 
                userBreakdownArray.append({
                    "name": "User",
                    "count": userCount
                })
                userBreakdownArray.append({
                    "name": "Admin",
                    "count": adminCount
                })

                return jsonify(userBreakdownArray)
            return make_response('User Breakdown Not Found', 404)

        except IOError:
            print("I/O error")
        except ValueError:
            print("Value Error")
        except:
            print("Unexpected error")
            raise
    else:
        return make_response('Request Forbidden', 403)


@ app.route('/get_province_vs_status_count/<date_range>', methods=['GET'])
def get_province_vs_status_count(date_range):
    # checking for authentication
    auth_res = authenticate_token(request.headers['authorization'])
    if(auth_res != False):
        # returns the count of different incident types in each province
        # this is used in metrics for visualization
        try:
            # this is for date range filtering
            duration = datetime.utcnow()
            if(date_range == "weekly"):
                # setting the duration upto last week
                duration = duration - relativedelta(weeks=1)
            elif(date_range == "monthly"):
                # setting the duration upto last month
                duration = duration - relativedelta(months=1)
            elif(date_range == "yearly"):
                # setting the duration upto last year
                duration = duration - relativedelta(years=1)
            # initializing array to count the incidents belong to a certain status
            statusDict = {
                "Pending Verification": 0,
                "Pending Treatment": 0,
                "Under Treatment": 0,
                "Recovering": 0,
                "Recovered": 0,
                "Death": 0,
                "Declined": 0,
            }
            cpDict = statusDict.copy()
            cpDict["province"] = "Central"
            epDict = statusDict.copy()
            epDict["province"] = "Eastern"
            ncDict = statusDict.copy()
            ncDict["province"] = "North Central"
            nwDict = statusDict.copy()
            nwDict["province"] = "North Western"
            npDict = statusDict.copy()
            npDict["province"] = "Northern"
            sgDict = statusDict.copy()
            sgDict["province"] = "Sabaragamuwa"
            spDict = statusDict.copy()
            spDict["province"] = "Southern"
            upDict = statusDict.copy()
            upDict["province"] = "Uva"
            wpDict = statusDict.copy()
            wpDict["province"] = "Western"
            provinceStatusArray = [cpDict, epDict, ncDict, nwDict, npDict, sgDict, spDict, upDict, wpDict]
            incidentCount = {}
            if(date_range == "all"):
                incidentCount = db.session.query(Incident.province, PatientStatus.status, func.count(Incident.patient_status_id)).filter().join(PatientStatus).group_by(Incident.province, Incident.patient_status_id).all()
            else:
                incidentCount = db.session.query(Incident.province, PatientStatus.status, func.count(Incident.patient_status_id)).filter(Incident.reported_time >= duration).join(PatientStatus).group_by(Incident.province, Incident.patient_status_id).all()
            db.session.commit()
            if(incidentCount != {}): 
                for x in incidentCount:
                    province = x[0]
                    status = x[1]
                    count = x[2]

                for item in provinceStatusArray:
                    if(item["province"] == province):
                        item[status] = count

                return jsonify(provinceStatusArray)
            return make_response('Incident Breakdown Not Found', 404)

        except IOError:
            print("I/O error")
        except ValueError:
            print("Value Error")
        except:
            print("Unexpected error")
            raise
    else:
        return make_response('Request Forbidden', 403)


@ app.route('/login_admin_user', methods=['POST'])
def login_admin_user():
    # login function for admin users
    try:
        email = request.json['user'].encode("utf-8")
        password  = request.json['pass'].encode("utf-8")

        loginAdmin = Admin.query.filter_by(email=email).first()
        db.session.commit()
        if(loginAdmin != {} and loginAdmin != None):
            userPass = loginAdmin.password.encode("utf-8")
            if bcrypt.checkpw(password, userPass):
                loggedInUser = {
                    "login_res": True,
                    "id": loginAdmin.id,
                    "email": loginAdmin.email,
                    "name" : loginAdmin.name,
                    "contact": loginAdmin.contact,
                    "org_id": loginAdmin.org_id
                }
                secret_key = SECRET_KEY
                token = jwt.encode({'user': loginAdmin.email, 'userId': loginAdmin.id, 'exp': datetime.utcnow(
                ) + relativedelta(days=1)}, secret_key)
                return jsonify({'token': token.decode('UTF-8'),'login_res': True, 'userData': loggedInUser})
            else:
                return make_response({"login_res": False}, 200)
        return make_response({"login_res": False}, 200)

    except IOError:
        print("I/O error")
    except ValueError:
        print("Value Error")
    except:
        print("Unexpected error")
        raise


@ app.route('/create_admin_user', methods=['POST'])
def create_admin_user():
    ## checking for authentication
    auth_res = authenticate_token(request.headers['authorization'])
    if(auth_res != False):
        # signup function for admin users
        try:
            email = request.json['email'].encode("utf-8")
            name  = request.json['name'].encode("utf-8")
            contact  = request.json['contact'].encode("utf-8")
            password  = request.json['password'].encode("utf-8")
            org_id  = request.json['orgId'].encode("utf-8")
            hashed_password = bcrypt.hashpw(password, bcrypt.gensalt())
            new_admin = Admin(email, name, contact, hashed_password, org_id)
            db.session.add(new_admin)
            db.session.commit()
            return user_schema.jsonify(new_admin)

        except IOError:
            print("I/O error")
        except ValueError:
            print("Value Error")
        except:
            print("Unexpected error")
            raise
    else:
        return make_response('Request Forbidden', 403)


@ app.route('/get_event_statuses', methods=['GET'])
def get_event_statuses():
    # checking for authentication
    auth_res = authenticate_token(request.headers['authorization'])
    if(auth_res != False):
        # returns all the patient statuses in the db
        eventStatus = EventStatus.query.order_by(EventStatus.id.asc()).all()
        db.session.commit()
        if(eventStatus != {}):
            result = event_statuses_schema.dump(eventStatus)
            return jsonify(result)
        return make_response('Event Status Not Found', 404)
    else:
        return make_response('Request Forbidden', 403)



@ app.route('/query_events', methods=['POST'])
def query_events():
    # checking for authentication
    auth_res = authenticate_token(request.headers['authorization'])
    if(auth_res != False):
        org_id = request.json['orgId']
        event_name = request.json['eventName']
        province = request.json['province']
        status = request.json['status']
        date_range = request.json['dateRange']
        duration = datetime.utcnow()
        if(date_range == "weekly"):
            # setting the duration upto last week
            duration = duration - relativedelta(weeks=1)
        elif(date_range == "monthly"):
            # setting the duration upto last month
            duration = duration - relativedelta(months=1)
        elif(date_range == "yearly"):
            # setting the duration upto last year
            duration = duration - relativedelta(years=1)

        try:
            # returns all the events based on the parameters provided
            if(date_range == "all"):
                # remove date range from the query
                if(status == "all"):
                    # remove event status from the query
                    if(province == "all"):
                    # remove province from the query
                        if(event_name == ""):
                            # remove event name from the query
                            events = db.session.query(Event, OrgUnit, EventStatus).join(OrgUnit).join(EventStatus).order_by(Event.start_time.desc()).all()
                        else:
                            events = db.session.query(Event, OrgUnit, EventStatus).filter(
                                Event.name.ilike("%"+event_name+"%")
                                ).join(OrgUnit).join(EventStatus).order_by(Event.start_time.desc()).all()
                    else:
                        if(event_name == ""):
                            # remove event name from the query
                            events = db.session.query(Event, OrgUnit, EventStatus).join(OrgUnit).join(EventStatus).filter(
                                OrgUnit.province == province, 
                                ).order_by(Event.start_time.desc()).all()
                        else:
                            events = db.session.query(Event, OrgUnit, EventStatus).join(OrgUnit).join(EventStatus).filter(
                                Event.name.ilike("%"+event_name+"%"),
                                OrgUnit.province == province, 
                                ).order_by(Event.start_time.desc()).all()
                else:
                    if(province == "all"):
                    # remove province from the query
                        if(event_name == ""):
                            # remove event name from the query
                            events = db.session.query(Event, OrgUnit, EventStatus).join(OrgUnit).join(EventStatus).filter(
                                Event.status_id == status,
                                ).order_by(Event.start_time.desc()).all()
                        else:
                            events = db.session.query(Event, OrgUnit, EventStatus).join(OrgUnit).join(EventStatus).filter(
                                Event.name.ilike("%"+event_name+"%"),
                                Event.status_id == status, 
                                ).order_by(Event.start_time.desc()).all()
                    else:
                        if(event_name == ""):
                            # remove event name from the query
                            events = db.session.query(Event, OrgUnit, EventStatus).join(OrgUnit).join(EventStatus).filter(
                                OrgUnit.province == province,
                                Event.status_id == status, 
                                ).order_by(Event.start_time.desc()).all()
                        else:
                            events = db.session.query(Event, OrgUnit, EventStatus).join(OrgUnit).join(EventStatus).filter(
                                Event.name.ilike("%"+event_name+"%"),
                                OrgUnit.province == province, 
                                Event.status_id == status,
                                ).order_by(Event.start_time.desc()).all()
            else:
                if(status == "all"):
                    # remove event status from the query
                    if(province == "all"):
                    # remove province from the query
                        if(event_name == ""):
                            # remove event name from the query
                            events = db.session.query(Event, OrgUnit, EventStatus).join(OrgUnit).join(EventStatus).filter(
                                Event.start_time >= duration 
                                ).order_by(Event.start_time.desc()).all()
                        else:
                            events = db.session.query(Event, OrgUnit, EventStatus).join(OrgUnit).join(EventStatus).filter(
                                Event.name.ilike("%"+event_name+"%"),
                                Event.start_time >= duration 
                                ).order_by(Event.start_time.desc()).all()
                    else:
                        if(event_name == ""):
                            # remove event name from the query
                            events = db.session.query(Event, OrgUnit, EventStatus).join(OrgUnit).join(EventStatus).filter(
                                OrgUnit.province == province, 
                                Event.start_time >= duration
                                ).order_by(Event.start_time.desc()).all()
                        else:
                            events = db.session.query(Event, OrgUnit, EventStatus).join(OrgUnit).join(EventStatus).filter(
                                Event.name.ilike("%"+event_name+"%"),
                                OrgUnit.province == province, 
                                Event.start_time >= duration
                                ).order_by(Event.start_time.desc()).all()
                else:
                    # remove event status from the query
                    if(province == "all"):
                    # remove province from the query
                        if(event_name == ""):
                            # remove event name from the query
                            events = db.session.query(Event, OrgUnit, EventStatus).join(OrgUnit).join(EventStatus).filter(
                                Event.status_id == status,
                                Event.start_time >= duration
                                ).order_by(Event.start_time.desc()).all()
                        else:
                            events = db.session.query(Event, OrgUnit, EventStatus).join(OrgUnit).join(EventStatus).filter(
                                Event.name.ilike("%"+event_name+"%"),
                                Event.status_id == status, 
                                Event.start_time >= duration
                                ).order_by(Event.start_time.desc()).all()
                    else:
                        if(event_name == ""):
                            # remove event name from the query
                            events = db.session.query(Event, OrgUnit, EventStatus).join(OrgUnit).join(EventStatus).filter(
                                OrgUnit.province == province,
                                Event.status_id == status,
                                Event.start_time >= duration 
                                ).order_by(Event.start_time.desc()).all()
                        else:
                            events = db.session.query(Event, OrgUnit, EventStatus).join(OrgUnit).join(EventStatus).filter(
                                Event.name.ilike("%"+event_name+"%"),
                                OrgUnit.province == province, 
                                Event.status_id == status,
                                Event.start_time >= duration
                                ).order_by(Event.start_time.desc()).all()

            db.session.commit()
            if(events != {}):
                result = events_with_full_schema.dump([{'event': x[0], 'org_unit': x[1], 'status': x[2]} for x in events])
                return jsonify(result)
            return make_response('Events Not Found', 404)

        except IOError:
            print("I/O error")
        except ValueError:
            print("Value Error")
        except:
            print("Unexpected error")
            raise 
    else:
        return make_response('Request Forbidden', 403)


@ app.route('/update_event_status/<event_id>/<new_status>', methods=['GET'])
def update_event_status(event_id, new_status):
    # checking for authentication
    auth_res = authenticate_token(request.headers['authorization'])
    if(auth_res != False):
        # returns the event related to the id provided
        try:
            updateEvent = Event.query.filter_by(id=event_id).first()
            if(updateEvent != {}):
                updateEvent.status_id = new_status
                db.session.commit()
                return make_response('Event Status Changed', 200)
            return make_response('Event Not Found', 404)

        except IOError:
            print("I/O error")
        except ValueError:
            print("Value Error")
        except:
            print("Unexpected error")
            raise
    else:
        return make_response('Request Forbidden', 403)


@app.route('/create_event', methods=['POST'])
def create_event():
    # this will create a new event
     # checking for authentication
    auth_res = authenticate_token(request.headers['authorization'])
    if(auth_res != False):
        try:
            print(request)
            name = request.json['name']
            venue = request.json['venue']
            location_lat = request.json['location_lat']
            location_long = request.json['location_long']
            start_timestamp = request.json['start_time']
            # converts time to python datetime format
            start_time = datetime.fromtimestamp(start_timestamp/1000.0)
            duration = request.json['duration']
            coordinator_name = request.json['coordinator_name']
            coordinator_contact = request.json['coordinator_contact']
            status_id = request.json['status_id']
            org_id = request.json['org_id']
            created_by = request.json['created_by']
            description = request.json['description']
            new_event = Event(name, venue, location_lat, location_long, start_time, duration, coordinator_name,
            coordinator_contact, status_id, org_id, created_by, description)
            db.session.add(new_event)
            db.session.commit()
            return event_schema.jsonify(new_event)

        except IOError:
            print("I/O error")
        except ValueError:
            print("Value Error")
        except:
            print("Unexpected error")
            raise
    else:
       return make_response('Request Forbidden', 403) 


# running server
if __name__ == '__main__':
    app.run(debug=True)
