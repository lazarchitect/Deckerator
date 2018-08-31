<?php 

phpinfo();

if (isset($_POST['username']) and isset($_POST['password'])){

	$vari = "Eddie!"

	$dbhost="den1.mysql3.gear.host";  // hostname
	$dbuser="deckerator"; // mysql username
	$dbpass="Kin5$tork4"; // mysql password
	$db="deckerator"; // database you want to use
	
	echo "Attempting Connection"; 
	$conn=mysqli_connect($dbhost, $dbuser, $dbpass, $db) or die("Connection failed.");
	echo "Connection achieved";
	
	$username = $_POST['username'];
	$password = $_POST['password'];
	
	echo "Attempting to query database";
	$query = "SELECT from users WHERE username='.$username' AND password='.$password'";
	$execute = mysqli_query($conn, $query);
	echo "query achieved";

	$num = mysqli_num_rows($execute);

	if($num == 1){

		// session_start();
		// $_SESSION['username']=$username;
		header("location: homepage.php");
	}
 
	else{
		header("location: loginfail.html");
	}
}

else{
	// header("location: loginfail.html");
	$vari = "unsuccessful.";
}

?>

<html>
<head>
	<title>processing</title>
</head>
<body>
	<h4>Processing input....</h4>

	<?php print $vari; ?>


</body>
</html>