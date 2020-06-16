import 'dart:core';

// this class corresponds to the user table
class User {
  // id is auto incremented in the database
  int id;
  int telephone;
  String firstName;
  String lastName;
  String nicNumber; // not required
  String email; // not required
  String password;

  User(
      {this.id,
      this.telephone,
      this.firstName,
      this.lastName,
      this.nicNumber,
      this.email,
      this.password});

  Map toJson() => {
    'id': id,
    'telephone': telephone,
    'firstName': firstName,
    'lastName': lastName,
    'nicNumber': nicNumber,
    'email': email,
    'password': password
  };

  factory User.fromJson(Map<String, dynamic> json) {
    return User(
        id: json['id'] as int,
        telephone: json['telephone'] as int,
        firstName: json['first_name'] as String,
        lastName: json['last_name'] as String,
        nicNumber: json['nic_number'] as String,
        email: json['email'] as String,
        password: json['password'] as String);
  }
}